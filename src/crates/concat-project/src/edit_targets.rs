// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 EditPop contributors

//! Resolves a phone's single-clip transition action to an actual cut.
use crate::model::Timeline;

/// Prefer the selected clip's incoming seam. If it is the first clip,
/// use its outgoing seam instead. Gaps, other tracks and sound-only
/// clips never become implicit transition targets.
pub fn phone_transition_cut(timeline: &Timeline, selected: &str) -> Option<String> {
    let clip = timeline.clip(selected)?;
    if !clip.kind.is_visual() {
        return None;
    }
    let frame = timeline.video.rate_den as f64 / timeline.video.rate_num.max(1) as f64;
    let meets = |end: f64, start: f64| (end - start).abs() < frame / 2.0;
    let incoming = timeline.clips.iter().any(|other| {
        other.id != clip.id
            && other.kind.is_visual()
            && other.track_id == clip.track_id
            && meets(other.start + other.duration, clip.start)
    });
    if incoming {
        return Some(clip.id.clone());
    }
    timeline
        .clips
        .iter()
        .find(|other| {
            other.id != clip.id
                && other.kind.is_visual()
                && other.track_id == clip.track_id
                && meets(clip.start + clip.duration, other.start)
        })
        .map(|other| other.id.clone())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::commands::ClipPatch;
    use crate::model::{AppliedFilter, Clip, ClipKind, Transition};
    use crate::{Command, DocumentSettings, Editor};
    use std::sync::Arc;

    fn timeline() -> Timeline {
        let mut t = Timeline::default();
        t.clips = vec![
            Arc::new(Clip::blank("left", "T1", ClipKind::Video, "left", 0.0, 2.0)),
            Arc::new(Clip::blank(
                "right",
                "T1",
                ClipKind::Video,
                "right",
                2.0,
                2.0,
            )),
        ];
        t
    }

    #[test]
    fn either_side_of_the_cut_resolves_to_the_incoming_clip() {
        let t = timeline();
        assert_eq!(phone_transition_cut(&t, "left").as_deref(), Some("right"));
        assert_eq!(phone_transition_cut(&t, "right").as_deref(), Some("right"));
        assert_eq!(phone_transition_cut(&t, "missing"), None);
    }

    #[test]
    fn gaps_other_tracks_and_audio_are_not_cuts() {
        for change in 0..3 {
            let mut t = timeline();
            let right = Arc::make_mut(&mut t.clips[1]);
            match change {
                0 => right.start += 0.1,
                1 => right.track_id = "T2".into(),
                _ => right.kind = ClipKind::Audio,
            }
            assert_eq!(phone_transition_cut(&t, "left"), None);
            assert_eq!(phone_transition_cut(&t, "right"), None);
        }
    }

    #[test]
    fn split_transition_effect_save_reopen_and_undo_preserve_the_edit() {
        let mut editor = Editor::new();
        let media = editor
            .apply(Command::AddMedia {
                item: crate::commands::NewMedia {
                    path: "/fixture.mp4".into(),
                    name: "Fixture".into(),
                    duration: Some(4.0),
                    kind: crate::model::MediaKind::Video,
                    width: Some(320),
                    height: Some(180),
                    frame_rate: Some(30.0),
                    frame_rate_fraction: Some("30/1".into()),
                    video_codec: Some("h264".into()),
                    audio_codec: Some("aac".into()),
                    has_audio: true,
                    audio_tracks: Vec::new(),
                    origin: None,
                    color_space: Default::default(),
                },
            })
            .expect("media")
            .created_id
            .expect("media id");
        editor
            .apply(Command::AddClip {
                media_id: media,
                track_id: "T1".into(),
                start: 0.0,
                ripple: false,
            })
            .expect("clip");
        let first = editor.project().active().clips[0].id.clone();
        let original_duration = editor.project().active().clips[0].duration;
        editor
            .apply(Command::SplitClips {
                clip_ids: vec![first.clone()],
                time: 2.0,
            })
            .expect("split");
        let timeline = editor.project().active();
        assert_eq!(timeline.clips.len(), 2);
        let incoming = phone_transition_cut(timeline, &first).expect("seam");
        let right = timeline.clip(&incoming).unwrap();
        assert_eq!(right.start, 2.0);
        assert_eq!(
            right.duration + timeline.clip(&first).unwrap().duration,
            original_duration
        );
        editor
            .apply(Command::UpdateClip {
                clip_id: incoming.clone(),
                patch: ClipPatch {
                    transition_in: Some(Some(Transition {
                        id: "concat.dissolve".into(),
                        duration: 0.5,
                        params: Default::default(),
                    })),
                    video_effects: Some(vec![AppliedFilter::new("concat.pixelate")]),
                    ..Default::default()
                },
            })
            .expect("finish");
        assert!(editor.undo());
        assert!(
            editor
                .project()
                .active()
                .clip(&incoming)
                .unwrap()
                .transition_in
                .is_none()
        );
        assert!(editor.redo());
        let document = editor.to_document(&DocumentSettings {
            name: "Fixture".into(),
            width: 1080,
            height: 1920,
            rate_num: 30,
            rate_den: 1,
        });
        let reopened = Editor::from_document(&document).expect("reopen");
        let right = reopened.project().active().clip(&incoming).unwrap();
        assert_eq!(right.transition_in.as_ref().unwrap().duration, 0.5);
        assert_eq!(right.video_effects[0].id, "concat.pixelate");
        assert_eq!(right.start, 2.0);
        assert_eq!(right.duration, original_duration - 2.0);
    }
}
