// ══════════════════════════════════════════════════════════════════
// crypto.rs — 满全法加密层 (Rust FFI)
// ══════════════════════════════════════════════════════════════════
//
// 对应 C 版 core/mqf_crypto.c。
// 通过 extern "C" 链接系统 libsodium (X25519) + libcrypto.so.3
// (AES-256-GCM + HKDF-SHA256)。所有符号均为手工声明, 类型用
// Opaque stub struct + 指针 — 不需要 C 头文件。
//
// 零 MIT/GPL/Apache 外部依赖, 仅链接系统自带。

// ── 错误码 ───────────────────────────────────────────────
pub const CRYPTO_OK: i32 = 0;
pub const CRYPTO_ERR: i32 = -1;
pub const CRYPTO_NOMEM: i32 = -2;
pub const CRYPTO_AUTH: i32 = -3;
pub const CRYPTO_REPLAY: i32 = -4;

// ── 常量 ─────────────────────────────────────────────────
pub const PUBKEY_LEN: usize = 32;
pub const PRIVKEY_LEN: usize = 32;
pub const SHARED_LEN: usize = 32;
pub const SESSION_LEN: usize = 32;
pub const GCM_NONCE_LEN: usize = 12;
pub const GCM_TAG_LEN: usize = 16;

const NONCE_WINDOW_SEC: u64 = 300;
const NONCE_HIST: usize = 512;

// ── Opaque stub 类型 (大小未知, 只用指针) ────────────────
#[repr(C)]
struct EvpCtx { _p: [u8; 0] }
#[repr(C)]
struct EvpCipher { _p: [u8; 0] }
#[repr(C)]
struct EvpPkeyCtx { _p: [u8; 0] }

// ═══════════════════════════════════════════════════════════
// extern libsodium
// ═══════════════════════════════════════════════════════════
#[link(name = "sodium")]
extern "C" {
    fn crypto_scalarmult_curve25519(q: *mut u8, n: *const u8, p: *const u8) -> i32;
    fn crypto_scalarmult_curve25519_base(q: *mut u8, n: *const u8) -> i32;
    fn randombytes_buf(buf: *mut u8, size: usize);
    fn sodium_memzero(pnt: *mut u8, len: usize);
}

// ═══════════════════════════════════════════════════════════
// extern libcrypto (OpenSSL 3)
// ═══════════════════════════════════════════════════════════
#[link(name = "crypto")]
extern "C" {
    fn EVP_CIPHER_CTX_new() -> *mut EvpCtx;
    fn EVP_CIPHER_CTX_free(ctx: *mut EvpCtx);

    fn EVP_EncryptInit_ex2(
        ctx: *mut EvpCtx,
        type_: *const EvpCipher,
        key: *const u8,
        iv: *const u8,
        params: *const u8,
    ) -> i32;
    fn EVP_DecryptInit_ex2(
        ctx: *mut EvpCtx,
        type_: *const EvpCipher,
        key: *const u8,
        iv: *const u8,
        params: *const u8,
    ) -> i32;

    fn EVP_EncryptUpdate(
        ctx: *mut EvpCtx,
        out: *mut u8,
        outl: *mut i32,
        inp: *const u8,
        inl: i32,
    ) -> i32;
    fn EVP_DecryptUpdate(
        ctx: *mut EvpCtx,
        out: *mut u8,
        outl: *mut i32,
        inp: *const u8,
        inl: i32,
    ) -> i32;

    fn EVP_EncryptFinal_ex(ctx: *mut EvpCtx, out: *mut u8, outl: *mut i32) -> i32;
    fn EVP_DecryptFinal_ex(ctx: *mut EvpCtx, out: *mut u8, outl: *mut i32) -> i32;

    fn EVP_CIPHER_CTX_ctrl(ctx: *mut EvpCtx, type_: i32, arg: i32, ptr: *mut u8) -> i32;

    fn EVP_aes_256_gcm() -> *const EvpCipher;
    fn EVP_sha256() -> *const EvpCipher;

    fn EVP_PKEY_CTX_new_id(type_: i32, e: *const u8) -> *mut EvpPkeyCtx;
    fn EVP_PKEY_derive_init(ctx: *mut EvpPkeyCtx) -> i32;
    fn EVP_PKEY_derive(ctx: *mut EvpPkeyCtx, key: *mut u8, keylen: *mut usize) -> i32;
    fn EVP_PKEY_CTX_set_hkdf_mode(ctx: *mut EvpPkeyCtx, mode: i32) -> i32;
    fn EVP_PKEY_CTX_set_hkdf_md(ctx: *mut EvpPkeyCtx, md: *const EvpCipher) -> i32;
    fn EVP_PKEY_CTX_set1_hkdf_key(ctx: *mut EvpPkeyCtx, key: *const u8, keylen: usize) -> i32;
    fn EVP_PKEY_CTX_set1_hkdf_salt(ctx: *mut EvpPkeyCtx, salt: *const u8, saltlen: usize) -> i32;
    fn EVP_PKEY_CTX_add1_hkdf_info(ctx: *mut EvpPkeyCtx, info: *const u8, infolen: usize) -> i32;
    fn EVP_PKEY_CTX_free(ctx: *mut EvpPkeyCtx);

    /* ── 一次性 SHA-256 (OpenSSL 3 low-level) ── */
    fn SHA256(data: *const u8, len: usize, md: *mut u8) -> *mut u8;
    fn SHA512(data: *const u8, len: usize, md: *mut u8) -> *mut u8;
}

// EVP_PKEY 的常量 (OpenSSL 3)
const EVP_PKEY_HKDF: i32 = 1036;
const EVP_PKEY_HKDEF_MODE_EXTRACT_AND_EXPAND: i32 = 0;
const EVP_CTRL_GCM_SET_IVLEN: i32 = 0x09;
const EVP_CTRL_GCM_GET_TAG: i32 = 0x10;
const EVP_CTRL_GCM_SET_TAG: i32 = 0x11;

// ── 安全工具 ─────────────────────────────────────────────
fn secure_zero(buf: &mut [u8]) {
    unsafe { sodium_memzero(buf.as_mut_ptr(), buf.len()) }
}

pub fn secure_random(buf: &mut [u8]) {
    unsafe { randombytes_buf(buf.as_mut_ptr(), buf.len()) }
}

// ═══════════════════════════════════════════════════════════
// X25519 密钥对
// ═══════════════════════════════════════════════════════════
pub struct Keypair {
    pub pub_: [u8; PUBKEY_LEN],
    priv_: [u8; PRIVKEY_LEN],
}

impl Keypair {
    pub fn generate() -> Option<Self> {
        let mut kp = Self {
            pub_: [0u8; PUBKEY_LEN],
            priv_: [0u8; PRIVKEY_LEN],
        };
        secure_random(&mut kp.priv_);
        // Curve25519 clamping (与 C 版完全对齐)
        kp.priv_[0] &= 248;
        kp.priv_[31] &= 127;
        kp.priv_[31] |= 64;
        let rc = unsafe {
            crypto_scalarmult_curve25519_base(kp.pub_.as_mut_ptr(), kp.priv_.as_ptr())
        };
        if rc != 0 {
            secure_zero(&mut kp.priv_);
            return None;
        }
        Some(kp)
    }

    pub fn from_seed(seed: &[u8; PRIVKEY_LEN]) -> Option<Self> {
        let mut kp = Self {
            pub_: [0u8; PUBKEY_LEN],
            priv_: *seed,
        };
        kp.priv_[0] &= 248;
        kp.priv_[31] &= 127;
        kp.priv_[31] |= 64;
        let rc = unsafe {
            crypto_scalarmult_curve25519_base(kp.pub_.as_mut_ptr(), kp.priv_.as_ptr())
        };
        if rc != 0 {
            return None;
        }
        Some(kp)
    }

    pub fn derive_shared(&self, peer_pub: &[u8; PUBKEY_LEN]) -> Option<[u8; SHARED_LEN]> {
        let mut out = [0u8; SHARED_LEN];
        let rc = unsafe {
            crypto_scalarmult_curve25519(out.as_mut_ptr(), self.priv_.as_ptr(), peer_pub.as_ptr())
        };
        if rc != 0 {
            return None;
        }
        Some(out)
    }
}

impl Drop for Keypair {
    fn drop(&mut self) {
        secure_zero(&mut self.priv_);
    }
}

// ═══════════════════════════════════════════════════════════
// SHA-256 / SHA-512 one-shot
// ═══════════════════════════════════════════════════════════
const SHA256_DIGEST_LEN: usize = 32;
const SHA512_DIGEST_LEN: usize = 64;

pub fn sha256(data: &[u8]) -> [u8; SHA256_DIGEST_LEN] {
    let mut out = [0u8; SHA256_DIGEST_LEN];
    unsafe {
        SHA256(data.as_ptr(), data.len(), out.as_mut_ptr());
    }
    out
}

pub fn sha512(data: &[u8]) -> [u8; SHA512_DIGEST_LEN] {
    let mut out = [0u8; SHA512_DIGEST_LEN];
    unsafe {
        SHA512(data.as_ptr(), data.len(), out.as_mut_ptr());
    }
    out
}

// ═══════════════════════════════════════════════════════════
// AES-256-GCM
// ═══════════════════════════════════════════════════════════
pub fn gcm_encrypt(
    key: &[u8; SESSION_LEN],
    nonce: &[u8; GCM_NONCE_LEN],
    aad: Option<&[u8]>,
    pt: &[u8],
    ct: &mut [u8],
    tag: &mut [u8; GCM_TAG_LEN],
) -> i32 {
    if ct.len() < pt.len() {
        return CRYPTO_ERR;
    }
    unsafe {
        let ctx = EVP_CIPHER_CTX_new();
        if ctx.is_null() {
            return CRYPTO_NOMEM;
        }
        let rc = gcm_encrypt_inner(ctx, key, nonce, aad, pt, ct, tag);
        EVP_CIPHER_CTX_free(ctx);
        rc
    }
}

unsafe fn gcm_encrypt_inner(
    ctx: *mut EvpCtx,
    key: &[u8; SESSION_LEN],
    nonce: &[u8; GCM_NONCE_LEN],
    aad: Option<&[u8]>,
    pt: &[u8],
    ct: &mut [u8],
    tag: &mut [u8; GCM_TAG_LEN],
) -> i32 {
    if EVP_EncryptInit_ex2(ctx, EVP_aes_256_gcm(), key.as_ptr(), nonce.as_ptr(), std::ptr::null()) != 1 {
        return CRYPTO_ERR;
    }
    if EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, GCM_NONCE_LEN as i32, std::ptr::null_mut()) != 1 {
        return CRYPTO_ERR;
    }
    if let Some(a) = aad {
        if !a.is_empty() {
            let mut aad_l: i32 = 0;
            if EVP_EncryptUpdate(ctx, std::ptr::null_mut(), &mut aad_l, a.as_ptr(), a.len() as i32) != 1 {
                return CRYPTO_ERR;
            }
        }
    }
    if !pt.is_empty() {
        let mut ct_l: i32 = 0;
        if EVP_EncryptUpdate(ctx, ct.as_mut_ptr(), &mut ct_l, pt.as_ptr(), pt.len() as i32) != 1 {
            return CRYPTO_ERR;
        }
    }
    // EVP_EncryptFinal_ex: GCM 模式无实际输出, 但必须调用以触发认证标签计算
    let mut fin = [0u8; 16];
    let mut fin_l: i32 = 0;
    if EVP_EncryptFinal_ex(ctx, fin.as_mut_ptr(), &mut fin_l) != 1 {
        return CRYPTO_ERR;
    }
    if EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, GCM_TAG_LEN as i32, tag.as_mut_ptr()) != 1 {
        return CRYPTO_ERR;
    }
    CRYPTO_OK
}

pub fn gcm_decrypt(
    key: &[u8; SESSION_LEN],
    nonce: &[u8; GCM_NONCE_LEN],
    aad: Option<&[u8]>,
    ct: &[u8],
    tag: &[u8; GCM_TAG_LEN],
    pt: &mut [u8],
) -> i32 {
    if pt.len() < ct.len() {
        return CRYPTO_ERR;
    }
    unsafe {
        let ctx = EVP_CIPHER_CTX_new();
        if ctx.is_null() {
            return CRYPTO_NOMEM;
        }
        let rc = gcm_decrypt_inner(ctx, key, nonce, aad, ct, tag, pt);
        EVP_CIPHER_CTX_free(ctx);
        rc
    }
}

unsafe fn gcm_decrypt_inner(
    ctx: *mut EvpCtx,
    key: &[u8; SESSION_LEN],
    nonce: &[u8; GCM_NONCE_LEN],
    aad: Option<&[u8]>,
    ct: &[u8],
    tag: &[u8; GCM_TAG_LEN],
    pt: &mut [u8],
) -> i32 {
    if EVP_DecryptInit_ex2(ctx, EVP_aes_256_gcm(), key.as_ptr(), nonce.as_ptr(), std::ptr::null()) != 1 {
        return CRYPTO_AUTH;
    }
    if EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, GCM_NONCE_LEN as i32, std::ptr::null_mut()) != 1 {
        return CRYPTO_AUTH;
    }
    if let Some(a) = aad {
        if !a.is_empty() {
            let mut aad_l: i32 = 0;
            if EVP_DecryptUpdate(ctx, std::ptr::null_mut(), &mut aad_l, a.as_ptr(), a.len() as i32) != 1 {
                return CRYPTO_AUTH;
            }
        }
    }
    if !ct.is_empty() {
        let mut pt_l: i32 = 0;
        if EVP_DecryptUpdate(ctx, pt.as_mut_ptr(), &mut pt_l, ct.as_ptr(), ct.len() as i32) != 1 {
            return CRYPTO_AUTH;
        }
    }
    if EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, GCM_TAG_LEN as i32, tag.as_ptr() as *mut u8) != 1 {
        return CRYPTO_AUTH;
    }
    let mut fin_l: i32 = 0;
    let mut fin = [0u8; 16];
    if EVP_DecryptFinal_ex(ctx, fin.as_mut_ptr(), &mut fin_l) != 1 {
        return CRYPTO_AUTH;
    }
    CRYPTO_OK
}

// ═══════════════════════════════════════════════════════════
// HKDF-SHA256 (OpenSSL 3)
// ═══════════════════════════════════════════════════════════
pub fn hkdf_sha256(
    ikm: &[u8],
    salt: Option<&[u8]>,
    info: Option<&[u8]>,
    okm: &mut [u8],
) -> i32 {
    unsafe {
        let pctx = EVP_PKEY_CTX_new_id(EVP_PKEY_HKDF, std::ptr::null());
        if pctx.is_null() {
            return CRYPTO_NOMEM;
        }
        let rc = hkdf_inner(pctx, ikm, salt, info, okm);
        EVP_PKEY_CTX_free(pctx);
        rc
    }
}

unsafe fn hkdf_inner(
    pctx: *mut EvpPkeyCtx,
    ikm: &[u8],
    salt: Option<&[u8]>,
    info: Option<&[u8]>,
    okm: &mut [u8],
) -> i32 {
    if EVP_PKEY_derive_init(pctx) != 1 { return CRYPTO_ERR; }
    if EVP_PKEY_CTX_set_hkdf_mode(pctx, EVP_PKEY_HKDEF_MODE_EXTRACT_AND_EXPAND) != 1 { return CRYPTO_ERR; }
    if EVP_PKEY_CTX_set_hkdf_md(pctx, EVP_sha256()) != 1 { return CRYPTO_ERR; }
    if EVP_PKEY_CTX_set1_hkdf_key(pctx, ikm.as_ptr(), ikm.len()) != 1 { return CRYPTO_ERR; }
    if let Some(s) = salt {
        if !s.is_empty() {
            if EVP_PKEY_CTX_set1_hkdf_salt(pctx, s.as_ptr(), s.len()) != 1 { return CRYPTO_ERR; }
        }
    }
    if let Some(i) = info {
        if !i.is_empty() {
            if EVP_PKEY_CTX_add1_hkdf_info(pctx, i.as_ptr(), i.len()) != 1 { return CRYPTO_ERR; }
        }
    }
    let mut outlen = okm.len();
    if EVP_PKEY_derive(pctx, okm.as_mut_ptr(), &mut outlen) != 1 || outlen != okm.len() {
        return CRYPTO_ERR;
    }
    CRYPTO_OK
}

// ═══════════════════════════════════════════════════════════
// NonceTracker (纯 Rust, 无 FFI)
// ═══════════════════════════════════════════════════════════
pub struct NonceTracker {
    history: [u64; NONCE_HIST],
    head: usize,
    count: usize,
    _window_us: u64,   // 预留 (C 版同款未启用)
}

impl NonceTracker {
    pub fn new() -> Self {
        Self {
            history: [0u64; NONCE_HIST],
            head: 0,
            count: 0,
            _window_us: NONCE_WINDOW_SEC * 1_000_000,
        }
    }

    pub fn check_and_mark(&mut self, nonce: u64, _now_us: u64) -> i32 {
        if self.history[..self.count].contains(&nonce) {
            return CRYPTO_REPLAY;
        }
        let pos = (self.head + self.count) % NONCE_HIST;
        self.history[pos] = nonce;
        if self.count == NONCE_HIST {
            self.head = (self.head + 1) % NONCE_HIST;
        } else {
            self.count += 1;
        }
        CRYPTO_OK
    }
}

// ═══════════════════════════════════════════════════════════
// 会话握手 (唤魂/招魂)
// ═══════════════════════════════════════════════════════════
pub struct Session {
    pub local_kp: Keypair,
    pub session_key: [u8; SESSION_LEN],
    pub peer_pub: [u8; PUBKEY_LEN],
    pub nonce_ctr: u64,
    pub has_peer: bool,
}

impl Session {
    pub fn huanhun() -> Option<Self> {
        let local_kp = Keypair::generate()?;
        Some(Self {
            local_kp,
            session_key: [0u8; SESSION_LEN],
            peer_pub: [0u8; PUBKEY_LEN],
            nonce_ctr: 1,
            has_peer: false,
        })
    }

    pub fn zhaohun(&mut self, peer_pub: &[u8; PUBKEY_LEN]) -> i32 {
        self.peer_pub = *peer_pub;
        self.has_peer = true;

        let shared = match self.local_kp.derive_shared(peer_pub) {
            Some(s) => s,
            None => return CRYPTO_ERR,
        };

        let info = b"mqf-session-v1\0";
        let rc = hkdf_sha256(&shared, None, Some(info), &mut self.session_key);
        secure_zero(&mut shared.clone());
        rc
    }

    pub fn encrypt_mccp(&mut self, mccp: &[u32], frame: &mut Vec<u8>) -> i32 {
        if !self.has_peer {
            return CRYPTO_ERR;
        }
        let pt_len = mccp.len() * 4;
        let total = GCM_NONCE_LEN + pt_len + GCM_TAG_LEN;
        frame.clear();
        frame.resize(total, 0);

        let mut nonce = [0u8; GCM_NONCE_LEN];
        secure_random(&mut nonce);
        nonce[0] = (self.nonce_ctr >> 24) as u8;
        nonce[1] = (self.nonce_ctr >> 16) as u8;
        nonce[2] = (self.nonce_ctr >> 8) as u8;
        nonce[3] = self.nonce_ctr as u8;

        // nonce 写入 frame 前 12B
        frame[..GCM_NONCE_LEN].copy_from_slice(&nonce);

        let pt_bytes = unsafe {
            std::slice::from_raw_parts(mccp.as_ptr() as *const u8, pt_len)
        };
        let mut tag = [0u8; GCM_TAG_LEN];
        let ct_off = GCM_NONCE_LEN;
        let rc = gcm_encrypt(
            &self.session_key,
            &nonce,
            None,
            pt_bytes,
            &mut frame[ct_off..ct_off + pt_len],
            &mut tag,
        );
        if rc != CRYPTO_OK {
            return rc;
        }
        // tag 追加到末尾
        let tag_off = ct_off + pt_len;
        frame[tag_off..].copy_from_slice(&tag);
        self.nonce_ctr += 1;
        CRYPTO_OK
    }

    pub fn decrypt_mccp(&self, frame: &[u8], mccp_out: &mut Vec<u32>) -> i32 {
        if frame.len() < GCM_NONCE_LEN + GCM_TAG_LEN {
            return CRYPTO_AUTH;
        }
        let pt_len = frame.len() - GCM_NONCE_LEN - GCM_TAG_LEN;
        if pt_len % 4 != 0 {
            return CRYPTO_AUTH;
        }

        let nonce = &frame[..GCM_NONCE_LEN];
        let ct = &frame[GCM_NONCE_LEN..GCM_NONCE_LEN + pt_len];
        let tag_arr: &[u8; GCM_TAG_LEN] = &frame[frame.len() - GCM_TAG_LEN..]
            .try_into().unwrap();

        let mut nonce_arr = [0u8; GCM_NONCE_LEN];
        nonce_arr.copy_from_slice(nonce);

        let mut pt = vec![0u8; pt_len];
        let rc = gcm_decrypt(&self.session_key, &nonce_arr, None, ct, tag_arr, &mut pt);
        if rc != CRYPTO_OK {
            return rc;
        }

        mccp_out.clear();
        mccp_out.extend(
            pt.chunks_exact(4)
                .map(|c| u32::from_ne_bytes([c[0], c[1], c[2], c[3]]))
        );
        CRYPTO_OK
    }
}

// ═══════════════════════════════════════════════════════════
// 测试 (对齐 C 版 test_crypto.c 同名测试)
// ═══════════════════════════════════════════════════════════
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn x25519_keygen_nonzero() {
        let kp = Keypair::generate().expect("keygen");
        assert!(kp.pub_.iter().any(|&b| b != 0));
        assert!(kp.priv_.iter().any(|&b| b != 0));
    }

    #[test]
    fn ecdh_agreement() {
        let a = Keypair::generate().unwrap();
        let b = Keypair::generate().unwrap();
        let sa = a.derive_shared(&b.pub_).unwrap();
        let sb = b.derive_shared(&a.pub_).unwrap();
        assert_eq!(sa, sb);
    }

    #[test]
    fn aes_gcm_roundtrip() {
        let key = [0x42u8; SESSION_LEN];
        let nonce = [0xABu8; GCM_NONCE_LEN];
        let pt = "hello mqf 满全法".as_bytes();
        let mut ct = vec![0u8; pt.len()];
        let mut tag = [0u8; GCM_TAG_LEN];
        assert_eq!(gcm_encrypt(&key, &nonce, None, pt, &mut ct, &mut tag), CRYPTO_OK);

        let mut pt2 = vec![0u8; pt.len()];
        assert_eq!(gcm_decrypt(&key, &nonce, None, &ct, &tag, &mut pt2), CRYPTO_OK);
        assert_eq!(pt2, pt);
    }

    #[test]
    fn aes_gcm_tamper_ct() {
        let key = [0x42u8; SESSION_LEN];
        let nonce = [0xABu8; GCM_NONCE_LEN];
        let pt = b"hello mqf";
        let mut ct = vec![0u8; pt.len()];
        let mut tag = [0u8; GCM_TAG_LEN];
        gcm_encrypt(&key, &nonce, None, pt, &mut ct, &mut tag);

        // 篡改密文
        ct[0] ^= 0xFF;
        let mut pt2 = vec![0u8; pt.len()];
        assert_eq!(gcm_decrypt(&key, &nonce, None, &ct, &tag, &mut pt2), CRYPTO_AUTH);
        ct[0] ^= 0xFF; // 还原
    }

    #[test]
    fn aes_gcm_tamper_tag() {
        let key = [0x42u8; SESSION_LEN];
        let nonce = [0xABu8; GCM_NONCE_LEN];
        let pt = b"hello mqf";
        let mut ct = vec![0u8; pt.len()];
        let mut tag = [0u8; GCM_TAG_LEN];
        gcm_encrypt(&key, &nonce, None, pt, &mut ct, &mut tag);

        tag[0] ^= 0xFF;
        let mut pt2 = vec![0u8; pt.len()];
        assert_eq!(gcm_decrypt(&key, &nonce, None, &ct, &tag, &mut pt2), CRYPTO_AUTH);
    }

    #[test]
    fn nonce_tracker_replay() {
        let mut nt = NonceTracker::new();
        assert_eq!(nt.check_and_mark(100, 0), CRYPTO_OK);
        assert_eq!(nt.check_and_mark(100, 0), CRYPTO_REPLAY);
        assert_eq!(nt.check_and_mark(200, 0), CRYPTO_OK);
    }

    #[test]
    fn hkdf_deterministic() {
        let ikm = b"ikm-secret";
        let info = b"mqf-test";
        let mut okm1 = [0u8; 32];
        let mut okm2 = [0u8; 32];
        hkdf_sha256(ikm, None, Some(info), &mut okm1);
        hkdf_sha256(ikm, None, Some(info), &mut okm2);
        assert_eq!(okm1, okm2);
    }

    #[test]
    fn session_handshake() {
        let mut s = Session::huanhun().unwrap();
        // 自己握自己的手: 模拟 peer
        let peer = Session::huanhun().unwrap();
        let rc = s.zhaohun(&peer.local_kp.pub_);
        assert_eq!(rc, CRYPTO_OK);
        assert!(s.has_peer);
        assert!(s.session_key.iter().any(|&b| b != 0));
    }

    #[test]
    fn session_encrypt_decrypt_mccp() {
        // 建立双方会话
        let mut sa = Session::huanhun().unwrap();
        let mut sb = Session::huanhun().unwrap();
        sa.zhaohun(&sb.local_kp.pub_);
        sb.zhaohun(&sa.local_kp.pub_);

        let msg: Vec<u32> = vec![0x0ABC_1234, 0x7001_0001, 0xF000_0000, 0, 0x0ABC_1234];
        let mut frame = Vec::new();
        assert_eq!(sa.encrypt_mccp(&msg, &mut frame), CRYPTO_OK);

        let mut out = Vec::new();
        assert_eq!(sb.decrypt_mccp(&frame, &mut out), CRYPTO_OK);
        // 去掉末尾 padding: decrypt_mccp 把全部 pt 都读出来, 需要精确对比长度
        assert_eq!(out, msg);
    }
}
