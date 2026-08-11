// ══════════════════════════════════════════════════════════════════
// atmosphere.rs — 大气层 (温度 · 云 · 雨 · 日照 · 蒸散 · 风)
// ══════════════════════════════════════════════════════════════════
//
// 物理简化:
//   · 气温: T_mean(d) = T_0 + A·sin(2π(d-d_summer)/365) + 白噪声
//   · 太阳赤纬: δ = -23.44°·cos(2π(d+10)/365)
//   · 日照时数: N = (24/π)·acos(-tanφ·tanδ)
//   · PAR = f(太阳高度角·日照·云衰减)
//   · 雨: 季节 p 的 Bernoulli, Gamma(强度)
//   · Penman-Monteith 简化 ET ∝ 净辐射·VPD·风

use crate::crypto::sha256;

/// Bernoulli + Gamma 采样器 (确定性伪随机, 基于 day 做 stream hash)
fn hash_n(seed: u64, day: u64, salt: u8) -> u64 {
    let mut buf = Vec::with_capacity(8 + 8 + 1);
    buf.extend_from_slice(&seed.to_be_bytes());
    buf.extend_from_slice(&day.to_be_bytes());
    buf.push(salt);
    let h = sha256(&buf);
    u64::from_be_bytes([h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7]])
}

#[inline]
fn u01(seed: u64, day: u64, salt: u8) -> f64 {
    (hash_n(seed, day, salt) as f64) / (u64::MAX as f64 + 1.0)
}

#[derive(Clone, Debug)]
pub struct Atmosphere {
    pub air_temp_c: f64,
    pub rainfall_mm: f64,
    pub wind_speed_ms: f64,
    pub cloud_cover_pct: f64,
    pub sunshine_hours: f64,
    pub par_mj_m2_day: f64,     // 光合有效辐射
    pub potential_et_mm: f64,   // 潜在蒸散发
    pub co2_ppm: f64,
    pub lat_deg: f64,
    /// RNG 状态
    rng_state: u64,
}

impl Atmosphere {
    pub fn new(lat_deg: f64) -> Self {
        Self {
            air_temp_c: 18.0,
            rainfall_mm: 0.0,
            wind_speed_ms: 2.0,
            cloud_cover_pct: 40.0,
            sunshine_hours: 8.0,
            par_mj_m2_day: 18.0,
            potential_et_mm: 3.0,
            co2_ppm: 420.0,
            lat_deg,
            rng_state: 0x9E37_79B9_7F4A_7C15 ^ (lat_deg.to_bits()),
        }
    }

    fn next_rand(&mut self) -> f64 {
        // xorshift64 — 快, 不错的大气噪声
        let mut s = self.rng_state;
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        self.rng_state = s;
        (s as f64) / (u64::MAX as f64 + 1.0)
    }

    /// 日气温均值 (正弦季节曲线 + 噪声)
    fn seasonal_temp(&self, day: u64) -> f64 {
        let t = day as f64;
        let t0 = 16.0;       // 年均温
        let amp = 14.0;      // 季节振幅
        // 夏至在 d=172 左右
        let phase = 2.0 * std::f64::consts::PI * ((t - 172.0) / 365.0);
        t0 + amp * phase.sin()
    }

    /// 太阳赤纬 (度)
    pub fn solar_declination(day: u64) -> f64 {
        -23.44_f64.to_radians().cos() * std::f64::consts::PI / 180.0 * 23.44 * 180.0 / std::f64::consts::PI +
        (-2.0 * std::f64::consts::PI * ((day + 10) as f64 / 365.0)).cos() * 23.44
    }

    /// 日照时数 (h), h = (24/π)·acos(-tanφ·tanδ)
    fn day_length_h(lat_deg: f64, day: u64) -> f64 {
        let phi = lat_deg.to_radians();
        let decl = Self::solar_declination(day).to_radians();
        let t = (-phi.tan() * decl.tan()).clamp(-1.0, 1.0);
        let h = (24.0 / std::f64::consts::PI) * t.acos();
        h.clamp(0.0, 24.0)
    }

    /// 大气顶上太阳辐照度 (MJ/m²/day)
    fn extra_terrestrial_rad(lat_deg: f64, day: u64) -> f64 {
        let gsc = 0.0820; // MJ/m²/min
        let decl = Self::solar_declination(day).to_radians();
        let phi = lat_deg.to_radians();
        let ws = Self::day_length_h(lat_deg, day) * std::f64::consts::PI / 24.0; // sunset hour angle
        let dr = 1.0 + 0.033 * (2.0 * std::f64::consts::PI * day as f64 / 365.0).cos();
        let base = (24.0 * 60.0 / std::f64::consts::PI) * gsc * dr *
            (ws * phi.sin() * decl.sin() + phi.cos() * decl.cos() * ws.sin());
        base.max(0.0)
    }

    /// 日推进
    pub fn tick(&mut self, day: u64) {
        // 1. 气温
        let t_seas = self.seasonal_temp(day);
        let noise = (self.next_rand() - 0.5) * 5.0; // ±2.5°C 噪声
        // 冷锋/热浪罕见事件
        let event = if u01(self.rng_state, day, 0xA1) < 0.02 {
            (self.next_rand() - 0.5) * 10.0
        } else { 0.0 };
        self.air_temp_c = t_seas + noise + event;

        // 2. 日照
        let max_sun = Self::day_length_h(self.lat_deg, day);
        let cloud_pct = 30.0 + 40.0 * (Self::solar_declination(day).sin() + 1.0) / 2.0
            + (self.next_rand() - 0.5) * 20.0;
        self.cloud_cover_pct = cloud_pct.clamp(0.0, 100.0);
        self.sunshine_hours = max_sun * (1.0 - self.cloud_cover_pct / 100.0)
            .clamp(0.05, 1.0);

        // 3. 大气辐射 → PAR
        let ra = Self::extra_terrestrial_rad(self.lat_deg, day);
        let transmission = 0.70 - 0.25 * (self.cloud_cover_pct / 100.0); // 云衰减
        let r_surf = ra * transmission;       // MJ/m²/day
        let par_j = r_surf * 2.0e6 * 0.45;    // PAR (J), 0.45 光子占比
        self.par_mj_m2_day = par_j / 1.0e6;   // MJ/m²/day

        // 4. 降水 (Bernoulli 季节概率 + Gamma 强度)
        // 简化: sin_shape peaks in summer (北半球)
        let season_p = 0.28 + 0.32 * (Self::solar_declination(day).sin() + 1.0) / 2.0;
        let p_rain = season_p.clamp(0.05, 0.70);
        let r: f64 = u01(self.rng_state, day, 0xB2);
        self.rainfall_mm = if r < p_rain {
            // Gamma 强度 ~ 3..35 mm / event
            let shape = 2.0;
            let rate = 0.3;
            let g = self.gamma_sample(shape, rate);
            g.clamp(0.1, 60.0)
        } else {
            0.0
        };

        // 5. 风 (m/s)
        self.wind_speed_ms = (2.0 + (self.next_rand() - 0.5) * 4.0).clamp(0.0, 20.0);

        // 6. 潜在蒸散发 (Penman-Monteith 简化)
        // ET ∝ 净辐射 · 饱和水汽压差 · (0.5 + 0.5·u)
        let delta = 4098.0 * (0.6108 * (17.27 * self.air_temp_c /
            (self.air_temp_c + 237.3)).exp()) / (self.air_temp_c + 237.3).powi(2);
        let psy = ((293.0_f64 - 0.0065 * 100.0) / 293.0).powf(5.26_f64);
        let gamma = 0.665e-3 * 101.3 * psy;
        let es = 0.6108 * (17.27 * self.air_temp_c / (self.air_temp_c + 237.3)).exp();
        let ea = es * (50.0 / 100.0); // 假设相对湿度 50%
        let vpd = es - ea;
        let rn = r_surf * 0.77; // 净短波
        self.potential_et_mm =
            (0.408 * delta * rn + gamma * 900.0 / (self.air_temp_c + 273.0)
                * self.wind_speed_ms * vpd)
            / (delta + gamma * (1.0 + 0.34 * self.wind_speed_ms));
        self.potential_et_mm = self.potential_et_mm.max(0.0).min(20.0);
    }

    /// Marsaglia-Tsang Gamma 采样 (deterministic via self RNG)
    fn gamma_sample(&mut self, shape: f64, rate: f64) -> f64 {
        if shape < 1.0 {
            let u = self.next_rand();
            return self.gamma_sample(1.0 + shape, rate) * u.powf(1.0 / shape);
        }
        let d = shape - 1.0 / 3.0;
        let c = 1.0 / (9.0 * d).sqrt();
        loop {
            let x = self.next_rand();
            let mut v = 1.0 + c * (x + x * x - 1.0).sqrt_or(-1.0);
            if v <= 0.0 { continue; }
            v = v * v * v;
            let u = self.next_rand();
            if u < 1.0 - 0.0331 * (x * x) * (x * x) { return d * v / rate; }
            if u.ln() < 0.5 * x * x + d * (1.0 - v + v.ln()) { return d * v / rate; }
        }
    }

    /// 林冠衰减后的 PAR (Beer-Lambert)
    pub fn par_after_canopy(&self, lai: f64) -> f64 {
        let k = 0.5; // 消光系数 (阔叶)
        self.par_mj_m2_day * (-k * lai).exp()
    }

    pub fn hash_material(&self) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&self.air_temp_c.to_be_bytes());
        v.extend_from_slice(&self.rainfall_mm.to_be_bytes());
        v.extend_from_slice(&self.par_mj_m2_day.to_be_bytes());
        v.extend_from_slice(&self.rng_state.to_be_bytes());
        v
    }
}

trait SqrtOr {
    fn sqrt_or(self, fallback: f64) -> f64;
}
impl SqrtOr for f64 {
    fn sqrt_or(self, fallback: f64) -> f64 {
        if self >= 0.0 { self.sqrt() } else { fallback }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tick_no_panic() {
        let mut atm = Atmosphere::new(30.0);
        for d in 0..365 { atm.tick(d); }
        assert!(atm.air_temp_c > -50.0 && atm.air_temp_c < 60.0);
        assert!(atm.par_mj_m2_day >= 0.0);
        assert!(atm.potential_et_mm >= 0.0);
    }

    #[test]
    fn par_decreases_with_canopy() {
        let atm = Atmosphere::new(30.0);
        let bare = atm.par_after_canopy(0.0);
        let dense = atm.par_after_canopy(4.0);
        assert!(dense < bare, "canopy should attenuate PAR");
    }

    #[test]
    fn seasonal_temp_range() {
        let atm = Atmosphere::new(30.0);
        // 夏至 vs 冬至
        let t_summer = atm.seasonal_temp(172);
        let t_winter = atm.seasonal_temp(355);
        assert!(t_summer > t_winter);
    }
}
