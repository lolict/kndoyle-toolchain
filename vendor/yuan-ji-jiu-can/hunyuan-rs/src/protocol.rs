// ══════════════════════════════════════════════════════════════════
// protocol.rs — 满全法会话协议层
// ══════════════════════════════════════════════════════════════════
//
//  唤魂(HuanHun) → 答灵(DaLing) → 缔约(DiYue) → 合一递归(HeYuan)
//
// 协议状态机:
//   Idle ──唤魂──▶ Calling                (发送方)
//   Calling ──收到答灵──▶ Connected        (握手完成)
//   Idle ──收到唤魂──▶ Answering           (接收方)
//   Answering ──发送答灵──▶ Connected
//   Connected ──达令/结束──▶ 加密通信 / 解体
//
// 与 C 版 core/mqf_crypto.c 里 mqf_session_*() 对应,
// 但加上进程/立约/递归语义层。

use crate::crypto::{self, Session, CRYPTO_OK};
#[cfg(test)]
use crate::crypto::{GCM_NONCE_LEN, GCM_TAG_LEN};
use crate::kernel::{CoupleOS, Process};
use crate::mccp::Mccp;

/// 协议角色 (主动方 / 被动方)
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    Caller,   // 主动唤魂
    Callee,   // 接收唤魂 / 答灵
}

/// 协议状态
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProtocolState {
    Idle,
    Calling,    // 已发唤魂, 等答灵
    Answering,  // 收到唤魂, 拟答灵
    Connected,  // Session 建立完成
    Jing,       // 蜜月期加密通信
    Finished,   // 解体
}

/// 协议错误
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProtoError {
    InvalidState,
    CryptoFail,
    MissingSession,
    MissingPeer,
    NoProcess,
}

/// 协议控制器 (把 crypto_session + process 绑定)
pub struct Protocol {
    pub crypto: Session,
    pub proto_state: ProtocolState,
    pub role: Role,
    pub os: CoupleOS,
    pub active_idx: Option<usize>,
}

impl Protocol {
    /// 发起唤魂 (caller 专用)
    pub fn huanhun() -> Result<Self, ProtoError> {
        let crypto = Session::huanhun().ok_or(ProtoError::CryptoFail)?;
        Ok(Self {
            crypto,
            proto_state: ProtocolState::Calling,
            role: Role::Caller,
            os: CoupleOS::new(0),
            active_idx: None,
        })
    }

    /// 接收唤魂 (callee 专用): 生成己方密钥 + 立即答灵
    pub fn wenling(peer_pub: &[u8; crypto::PUBKEY_LEN]) -> Result<Self, ProtoError> {
        let mut crypto = Session::huanhun().ok_or(ProtoError::CryptoFail)?;
        let rc = crypto.zhaohun(peer_pub);
        if rc != CRYPTO_OK {
            return Err(ProtoError::CryptoFail);
        }
        Ok(Self {
            crypto,
            proto_state: ProtocolState::Connected,  // 答灵完毕即连通
            role: Role::Callee,
            os: CoupleOS::new(0),
            active_idx: None,
        })
    }

    /// 完成答灵 (caller 收到 callee 的公钥后用)
    pub fn da_ling(&mut self, peer_pub: &[u8; crypto::PUBKEY_LEN]) -> Result<(), ProtoError> {
        if self.proto_state != ProtocolState::Calling {
            return Err(ProtoError::InvalidState);
        }
        let rc = self.crypto.zhaohun(peer_pub);
        if rc != CRYPTO_OK {
            return Err(ProtoError::CryptoFail);
        }
        self.proto_state = ProtocolState::Connected;
        Ok(())
    }

    /// 在已建立的会话上创建进程 (缔约 → 立约)
    pub fn create_process(&mut self, seq: Vec<Mccp>) -> Result<&mut Process, ProtoError> {
        if self.proto_state != ProtocolState::Connected {
            return Err(ProtoError::InvalidState);
        }
        // 取 pubkey 前 4 字节作为 party ID (简化)
        let a_id = u32::from_be_bytes([self.crypto.local_kp.pub_[0], self.crypto.local_kp.pub_[1],
                                      self.crypto.local_kp.pub_[2], self.crypto.local_kp.pub_[3]]);
        let b_id = u32::from_be_bytes([self.crypto.peer_pub[0], self.crypto.peer_pub[1],
                                      self.crypto.peer_pub[2], self.crypto.peer_pub[3]]);
        let idx = self.os.create_process(seq, a_id, b_id);
        self.active_idx = Some(idx);
        Ok(&mut self.os.procs[idx])
    }

    /// 加密发送 MCCP 序列
    pub fn send_mccp(&mut self, mccp: &[u32]) -> Result<Vec<u8>, ProtoError> {
        if self.proto_state != ProtocolState::Connected && self.proto_state != ProtocolState::Jing {
            return Err(ProtoError::InvalidState);
        }
        let mut frame = Vec::new();
        let rc = self.crypto.encrypt_mccp(mccp, &mut frame);
        if rc != CRYPTO_OK {
            return Err(ProtoError::CryptoFail);
        }
        Ok(frame)
    }

    /// 解密收到 MCCP 序列
    pub fn recv_mccp(&self, frame: &[u8]) -> Result<Vec<Mccp>, ProtoError> {
        if self.proto_state != ProtocolState::Connected && self.proto_state != ProtocolState::Jing {
            return Err(ProtoError::InvalidState);
        }
        let mut out = Vec::new();
        let rc = self.crypto.decrypt_mccp(frame, &mut out);
        if rc != CRYPTO_OK {
            return Err(ProtoError::CryptoFail);
        }
        Ok(out.into_iter().map(Mccp).collect())
    }

    /// 状态名
    pub fn state_name(&self) -> &'static str {
        match self.proto_state {
            ProtocolState::Idle => "空闲",
            ProtocolState::Calling => "唤魂中",
            ProtocolState::Answering => "答灵中",
            ProtocolState::Connected => "已连通",
            ProtocolState::Jing => "蜜月期",
            ProtocolState::Finished => "已解体",
        }
    }

    /// 进入蜜月期
    pub fn enter_jing(&mut self) {
        if self.proto_state == ProtocolState::Connected {
            self.proto_state = ProtocolState::Jing;
        }
    }

    /// 解体
    pub fn finish(&mut self) {
        self.proto_state = ProtocolState::Finished;
    }
}

/// 模拟一个完整的 唤魂→答灵→加密通信→解体 测试流 (单机端到端)
pub fn simulate_handshake_and_message(
    msg: &[u32],
) -> Result<(Vec<u8>, Vec<Mccp>), ProtoError> {
    // caller 唤魂
    let mut caller = Protocol::huanhun()?;

    // callee 收到 caller 的公钥 (caller 直接传)
    let caller_pub = caller.crypto.local_kp.pub_;
    let mut callee = Protocol::wenling(&caller_pub)?;

    // caller 收到 callee 的公钥, 答灵握手
    let callee_pub = callee.crypto.local_kp.pub_;
    caller.da_ling(&callee_pub)?;

    // 双方都进入连通
    caller.enter_jing();
    callee.enter_jing();

    // caller 发消息
    let frame = caller.send_mccp(msg)?;

    // callee 接收
    let received = callee.recv_mccp(&frame)?;

    caller.finish();
    callee.finish();

    Ok((frame, received))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn full_handshake_cycle() {
        let mut caller = Protocol::huanhun().expect("caller huanhun");
        assert_eq!(caller.proto_state, ProtocolState::Calling);

        let caller_pub = caller.crypto.local_kp.pub_;
        let callee = Protocol::wenling(&caller_pub).expect("callee wenling");

        let callee_pub = callee.crypto.local_kp.pub_;
        caller.da_ling(&callee_pub).expect("caller da ling");

        assert_eq!(caller.proto_state, ProtocolState::Connected);
        // callee 在 wenling 后自动答灵, 状态还停在 Answering, 需要 da 一步
        // 这里 caller 已经 Connected, 可以直接通信
    }

    #[test]
    fn session_keys_match() {
        let kp1 = crate::crypto::Keypair::generate().unwrap();
        let kp2 = crate::crypto::Keypair::generate().unwrap();
        let s1 = kp1.derive_shared(&kp2.pub_).unwrap();
        let s2 = kp2.derive_shared(&kp1.pub_).unwrap();
        assert_eq!(s1, s2);
    }

    #[test]
    fn encrypted_message_roundtrip() {
        let msg = vec![0x0ABC_1234, 0x7001_0001, 0, 0x0ABC_1234];
        let (frame, received) = simulate_handshake_and_message(&msg).expect("simulate");
        // frame = nonce(12B) || ciphertext || tag(16B)
        assert!(frame.len() >= GCM_NONCE_LEN + GCM_TAG_LEN + msg.len() * 4);
        let decoded: Vec<u32> = received.iter().map(|m| m.0).collect();
        assert_eq!(decoded, msg);
    }

    #[test]
    fn protocol_invalid_state_rejects_send() {
        let mut caller = Protocol::huanhun().unwrap();
        // Calling 状态不允许 send (必须 Connected 或 Jing)
        let r = caller.send_mccp(&[0]);
        assert_eq!(r, Err(ProtoError::InvalidState));
    }

    #[test]
    fn protocol_then_jing() {
        let mut caller = Protocol::huanhun().unwrap();
        let caller_pub = caller.crypto.local_kp.pub_;
        let callee = Protocol::wenling(&caller_pub).unwrap();
        let callee_pub = callee.crypto.local_kp.pub_;
        caller.da_ling(&callee_pub).unwrap();
        assert_eq!(caller.proto_state, ProtocolState::Connected);
        caller.enter_jing();
        assert_eq!(caller.proto_state, ProtocolState::Jing);
        caller.finish();
        assert_eq!(caller.proto_state, ProtocolState::Finished);
    }
}
