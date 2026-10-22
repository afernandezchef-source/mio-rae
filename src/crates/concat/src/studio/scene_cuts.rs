// SPDX-License-Identifier: AGPL-3.0-or-later
//! Local scene proposals, isolated from the document until reviewed and applied.
use super::*;
use concat_core::time::Rational;
use concat_project::scene_cuts::{Sample, histogram, split_command, suggest};
use std::sync::atomic::{AtomicBool, Ordering};

pub(super) struct SceneReview {
    cancel: Arc<AtomicBool>,
    revision: u64,
    clip_id: String,
    busy: bool,
    progress: i32,
    times: Vec<f64>,
    chosen: Vec<bool>,
    message: String,
}

impl Drop for SceneReview {
    fn drop(&mut self) {
        self.cancel.store(true, Ordering::Relaxed);
    }
}

impl Studio {
    pub fn scene_cancel(&mut self) {
        self.scene_review = None;
    }

    pub fn scene_start(&mut self) {
        self.flush_commit();
        self.scene_cancel();
        let Some(id) = self.sole_selection() else {
            return;
        };
        let Some(clip) = self.clip(&id).cloned() else {
            return;
        };
        if clip.kind != model::ClipKind::Video
            || self.locked(&clip.track_id)
            || !clip.speed.is_finite()
            || clip.speed <= 0.0
            || clip.speed_curve.is_some()
            || !clip.duration.is_finite()
            || clip.duration < 2.0
        {
            self.notify("Selecciona un vídeo desbloqueado de al menos 2 s, con velocidad constante positiva.", true);
            return;
        }
        let Some(path) = self
            .project()
            .media
            .iter()
            .find(|m| m.id == clip.media_id)
            .map(|m| m.path.clone())
        else {
            return;
        };
        self.stop_glide();
        self.pause();
        let revision = self.revision;
        let fps = self.timeline().video.rate();
        let cancel = Arc::new(AtomicBool::new(false));
        self.scene_review = Some(SceneReview {
            cancel: cancel.clone(),
            revision,
            clip_id: id,
            busy: true,
            progress: 0,
            times: vec![],
            chosen: vec![],
            message: "Analizando cambios de escena en el teléfono…".into(),
        });
        let epoch = crate::host::project_epoch();
        let worker_cancel = cancel.clone();
        spawn_in_project(
            move || -> Result<Vec<f64>, String> {
                // Own tiny cache and decoder: never evicts the playback pool. No frames
                // retained in the sample list, at most 1200 RGB histograms (~115 KiB).
                let pool = concat_media::ReaderPool::new(1024 * 1024, 1);
                let step = 0.25_f64.max(clip.duration / 1199.0);
                let count = ((clip.duration / step).floor() as usize + 1).min(1200);
                let mut samples = Vec::with_capacity(count);
                let mut last = -1;
                for index in 0..count {
                    if worker_cancel.load(Ordering::Relaxed) {
                        return Err("cancelled".into());
                    }
                    let local = (index as f64 * step).min(clip.duration - 0.000001);
                    let source = clip.source_start + local * clip.speed;
                    let request = concat_media::FrameRequest::new(
                        &path,
                        Rational::new((source * 1_000_000.0).round() as i64, 1_000_000),
                        64,
                        36,
                    );
                    let frame = pool.source(&request).map_err(|e| {
                        format!("No se pudo analizar el vídeo: {e}. Comprueba que siga disponible.")
                    })?;
                    if worker_cancel.load(Ordering::Relaxed) {
                        return Err("cancelled".into());
                    }
                    samples.push(Sample {
                        at: local,
                        histogram: histogram(frame.pixels()),
                    });
                    let progress = ((index + 1) * 100 / count) as i32;
                    if progress != last {
                        last = progress;
                        let token = worker_cancel.clone();
                        on_ui_in_project(epoch, move |studio, _, _| {
                            if let Some(review) = studio.scene_review.as_mut()
                                && Arc::ptr_eq(&review.cancel, &token)
                            {
                                review.progress = progress;
                            }
                        });
                    }
                }
                Ok(suggest(&samples, clip.start, clip.duration, fps))
            },
            move |studio, _, _, result| {
                let Some(review) = studio.scene_review.as_mut() else {
                    return;
                };
                if !Arc::ptr_eq(&review.cancel, &cancel) || review.revision != studio.revision {
                    return;
                }
                review.busy = false;
                match result {
                    Ok(times) => {
                        review.chosen = vec![false; times.len()];
                        review.message = if times.is_empty() {
                            "No se detectaron cambios claros de escena. Puedes dividir manualmente."
                                .into()
                        } else {
                            "Revisa cada propuesta con Ver y marca los cortes que quieras. Muestreo aproximado; ajusta después por fotogramas. No elimina contenido ni añade transiciones.".into()
                        };
                        review.times = times;
                    }
                    Err(error) => {
                        review.message = error;
                    }
                }
            },
        );
    }

    pub fn scene_toggle(&mut self, index: i32) {
        if let Some(review) = self.scene_review.as_mut()
            && !review.busy
            && let Some(chosen) = review.chosen.get_mut(index as usize)
        {
            *chosen = !*chosen;
        }
    }

    pub fn scene_preview(&mut self, index: i32) {
        if let Some(at) = self
            .scene_review
            .as_ref()
            .and_then(|r| r.times.get(index as usize))
            .copied()
        {
            self.seek(at as f32);
        }
    }

    pub fn scene_apply(&mut self) {
        self.flush_commit();
        let Some(review) = self.scene_review.take() else {
            return;
        };
        if review.busy || review.revision != self.revision {
            self.notify(
                "El proyecto cambió. Vuelve a analizar el clip antes de aplicar cortes.",
                true,
            );
            return;
        }
        let Some(clip) = self.clip(&review.clip_id).cloned() else {
            return;
        };
        if self.locked(&clip.track_id) {
            self.notify("Desbloquea la pista antes de aplicar cortes.", true);
            return;
        }
        let times: Vec<_> = review
            .times
            .iter()
            .zip(&review.chosen)
            .filter_map(|(at, chosen)| chosen.then_some(*at))
            .collect();
        if let Some(command) = split_command(&clip.id, clip.start, clip.duration, &times) {
            self.apply(command);
            self.notify(
                "Cortes aplicados. Puedes deshacerlos en un solo paso.",
                false,
            );
        }
    }

    pub(super) fn publish_scene(&self, app: &App) {
        let editor = app.global::<crate::Editor>();
        let review = self.scene_review.as_ref();
        editor.set_scene_busy(review.is_some_and(|r| r.busy));
        editor.set_scene_message(
            review
                .map_or(
                    "Selecciona un vídeo y pulsa Analizar. Todo el análisis es local.",
                    |r| r.message.as_str(),
                )
                .into(),
        );
        editor.set_scene_progress(review.map_or(0, |r| r.progress));
        editor.set_scene_can_apply(review.is_some_and(|r| !r.busy && r.chosen.iter().any(|v| *v)));
        let rows: Vec<crate::SceneCutData> = review
            .map(|r| {
                r.times
                    .iter()
                    .zip(&r.chosen)
                    .map(|(at, chosen)| crate::SceneCutData {
                        label: frames_timecode(*at as f32, self.frame_rate()).into(),
                        chosen: *chosen,
                    })
                    .collect()
            })
            .unwrap_or_default();
        editor.set_scene_cuts(ModelRc::new(VecModel::from(rows)));
    }
}
