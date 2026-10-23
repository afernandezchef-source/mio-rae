// SPDX-License-Identifier: AGPL-3.0-or-later
// Spatial bilateral smoothing: no history, decoded frame queues or model.
struct Params { strength: f32 }

fn effect(uv: vec2<f32>) -> vec4<f32> {
    let center = sample(uv);
    let amount = clamp(params.strength / 100.0, 0.0, 1.0);
    if amount <= 0.0 || center.a <= 0.000001 {
        return center;
    }
    let sigma = 0.02 + amount * 0.12;
    let pixel = texel();
    var sum = vec3<f32>(0.0);
    var total = 0.0;
    for (var y: i32 = -2; y <= 2; y++) {
        for (var x: i32 = -2; x <= 2; x++) {
            let neighbor = sample(uv + vec2<f32>(f32(x), f32(y)) * pixel);
            let difference = neighbor.rgb - center.rgb;
            let spatial = exp(-f32(x * x + y * y) / 2.42);
            let similarity = exp(-dot(difference, difference) / (2.0 * sigma * sigma));
            // Hidden RGB must not bleed from a transparent neighbor.
            let weight = spatial * similarity * neighbor.a;
            sum += neighbor.rgb * weight;
            total += weight;
        }
    }
    let smoothed = sum / max(total, 0.000001);
    return vec4<f32>(mix(center.rgb, smoothed, amount), center.a);
}
