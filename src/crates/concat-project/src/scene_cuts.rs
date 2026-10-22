// SPDX-License-Identifier: AGPL-3.0-or-later
//! Conservative, bounded scene-change proposals. Analysis never edits a project.

use crate::Command;

#[derive(Clone, Debug)]
/// A small color summary at a sampled project-local time.
pub struct Sample {
    /// Seconds relative to the selected clip, in project time.
    pub at: f64,
    /// Eight normalized bins for each RGB channel.
    pub histogram: [f32; 24],
}

/// Summarize RGBA8 pixels without retaining the decoded image.
pub fn histogram(rgba: &[u8]) -> [f32; 24] {
    let mut bins = [0.0; 24];
    let count = rgba.len() / 4;
    if count == 0 {
        return bins;
    }
    for pixel in rgba.chunks_exact(4) {
        for channel in 0..3 {
            bins[channel * 8 + usize::from(pixel[channel]) / 32] += 1.0 / count as f32;
        }
    }
    bins
}

fn distance(a: &Sample, b: &Sample) -> f32 {
    a.histogram
        .iter()
        .zip(b.histogram)
        .map(|(a, b)| (a - b).abs())
        .sum::<f32>()
        / 6.0
}

/// At most twelve sustained changes, at least one second apart and from edges.
/// Rejects a single sampled flash. Times are snapped to the project's frame grid.
pub fn suggest(samples: &[Sample], start: f64, duration: f64, fps: f64) -> Vec<f64> {
    if !start.is_finite() || !duration.is_finite() || !fps.is_finite() || fps <= 0.0 {
        return vec![];
    }
    let mut candidates = Vec::new();
    for window in samples.windows(4) {
        let [earlier, before, current, after] = window else {
            unreachable!()
        };
        if window
            .iter()
            .any(|s| !s.at.is_finite() || s.histogram.iter().any(|n| !n.is_finite()))
            || window.windows(2).any(|w| w[0].at >= w[1].at)
        {
            continue;
        }
        let at = ((start + current.at) * fps).round() / fps;
        let score = distance(before, current).min(distance(before, after));
        if at - start >= 1.0
            && start + duration - at >= 1.0
            && score >= 0.35
            && distance(earlier, before) < 0.25
            && distance(current, after) < 0.25
        {
            candidates.push((at, score));
        }
    }
    candidates.sort_by(|a, b| b.1.total_cmp(&a.1));
    let mut chosen: Vec<f64> = Vec::new();
    for (at, _) in candidates {
        if chosen.len() < 12 && chosen.iter().all(|other| (other - at).abs() >= 1.0) {
            chosen.push(at);
        }
    }
    chosen.sort_by(f64::total_cmp);
    chosen
}

/// Descending cuts keep targeting the original left segment; one atomic undo.
pub fn split_command(id: &str, start: f64, duration: f64, times: &[f64]) -> Option<Command> {
    let mut times: Vec<_> = times
        .iter()
        .copied()
        .filter(|t| t.is_finite() && *t - start >= 1.0 && start + duration - *t >= 1.0)
        .collect();
    times.sort_by(|a, b| b.total_cmp(a));
    times.dedup();
    (!times.is_empty()).then(|| Command::Batch {
        commands: times
            .into_iter()
            .map(|time| Command::SplitClips {
                clip_ids: vec![id.to_owned()],
                time,
            })
            .collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn sample(at: f64, color: [u8; 4]) -> Sample {
        Sample {
            at,
            histogram: histogram(&color),
        }
    }
    #[test]
    fn sustained_change_and_flash() {
        let red = [255, 0, 0, 255];
        let blue = [0, 0, 255, 255];
        let frames: Vec<_> = (0..25)
            .map(|i| sample(i as f64 * 0.25, if i >= 12 { blue } else { red }))
            .collect();
        assert_eq!(suggest(&frames, 2.0, 6.0, 30.0), vec![5.0]);
        let flash: Vec<_> = (0..25)
            .map(|i| sample(i as f64 * 0.25, if i == 12 { blue } else { red }))
            .collect();
        assert!(suggest(&flash, 0.0, 6.0, 30.0).is_empty());
    }
    #[test]
    fn edges_invalid_times_and_frame_grid() {
        let frames: Vec<_> = (0..25)
            .map(|i| {
                sample(
                    i as f64 * 0.25,
                    if i >= 12 {
                        [255, 0, 0, 255]
                    } else {
                        [0, 0, 255, 255]
                    },
                )
            })
            .collect();
        let cuts = suggest(&frames, 1.013, 6.0, 30000.0 / 1001.0);
        assert_eq!(cuts.len(), 1);
        assert!((cuts[0] * 30000.0 / 1001.0 - (cuts[0] * 30000.0 / 1001.0).round()).abs() < 1e-9);
        assert!(suggest(&frames, 0.0, 0.5, 30.0).is_empty());
        assert!(suggest(&frames, 0.0, 6.0, f64::NAN).is_empty());
        let Some(Command::Batch { commands }) =
            split_command("c1", 0.0, 6.0, &[3.0, 2.0, 3.0, f64::NAN, 0.1])
        else {
            panic!()
        };
        assert_eq!(commands.len(), 2);
        assert!(matches!(&commands[0], Command::SplitClips { time, .. } if *time == 3.0));
    }

    #[test]
    fn long_material_has_bounded_spaced_proposals() {
        let samples: Vec<_> = (0..400)
            .map(|i| {
                sample(
                    i as f64 * 0.25,
                    if (i / 8) % 2 == 0 {
                        [255, 0, 0, 255]
                    } else {
                        [0, 0, 255, 255]
                    },
                )
            })
            .collect();
        let cuts = suggest(&samples, 0.0, 100.0, 30.0);
        assert_eq!(cuts.len(), 12);
        assert!(cuts.windows(2).all(|w| w[1] - w[0] >= 1.0));
        assert!(suggest(&[], 0.0, 100.0, 30.0).is_empty());
        assert!(split_command("c1", 0.0, 4.0, &[0.0, 4.0, f64::INFINITY]).is_none());
    }
}
