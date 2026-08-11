// ══════════════════════════════════════════════════════════════════
// log_ring.rs — 关系日志环 + Merkle 历史锚定
// ══════════════════════════════════════════════════════════════════
//
// append-only 关系状态日志:
//   - 每条都有 seq / kind / payload(bytes) / ts_us / prev_hash
//   - 整个日志链 hash-chained
//   - Merkle 根用于证明 "某时刻有某事"
//   - 反篡改: 任一记录改 → 链断裂
//
// 对应 Python prototype kernel/log_ring.py。零 sha crate — 复用 crypto::sha256.
use crate::crypto::sha256;

pub const HASH_LEN: usize = 32;

/// 十六进制 hash 工具
#[allow(dead_code)]
fn hex32(b: &[u8; HASH_LEN]) -> String {
    let mut s = String::with_capacity(64);
    for x in b { s.push_str(&format!("{:02x}", x)); }
    s
}

/// 单条日志记录
#[derive(Clone, Debug)]
pub struct LogEntry {
    pub seq: u64,
    pub kind: u32,
    pub payload: Vec<u8>,
    pub ts_us: u64,
    pub prev_hash: [u8; HASH_LEN],
    pub hash: [u8; HASH_LEN],
}

impl LogEntry {
    pub fn new(seq: u64, kind: u32, payload: &[u8], ts_us: u64,
               prev_hash: [u8; HASH_LEN]) -> Self {
        let mut e = Self {
            seq, kind,
            payload: payload.to_vec(),
            ts_us, prev_hash,
            hash: [0u8; HASH_LEN],
        };
        e.hash = e._compute_hash();
        e
    }

    fn _compute_hash(&self) -> [u8; HASH_LEN] {
        // material = seq || kind || ts_us || prev_hash || payload
        let mut m = Vec::with_capacity(8 + 4 + 8 + HASH_LEN + self.payload.len());
        m.extend_from_slice(&self.seq.to_be_bytes());
        m.extend_from_slice(&self.kind.to_be_bytes());
        m.extend_from_slice(&self.ts_us.to_be_bytes());
        m.extend_from_slice(&self.prev_hash);
        m.extend_from_slice(&self.payload);
        sha256(&m)
    }
}

/// Merkle 树
pub struct MerkleTree {
    pub hashes: Vec<[u8; HASH_LEN]>,
}

impl MerkleTree {
    /// 从叶子 hash 建 Merkle 树, 返回 root.
    pub fn root_from(leaves: &[[u8; HASH_LEN]]) -> Option<[u8; HASH_LEN]> {
        if leaves.is_empty() { return None; }
        let mut level: Vec<[u8; HASH_LEN]> = leaves.to_vec();
        while level.len() > 1 {
            let mut next = Vec::with_capacity((level.len() + 1) / 2);
            for pair in level.chunks(2) {
                if pair.len() == 2 {
                    let mut m = Vec::with_capacity(HASH_LEN*2);
                    m.extend_from_slice(&pair[0]);
                    m.extend_from_slice(&pair[1]);
                    next.push(sha256(&m));
                } else {
                    next.push(pair[0]);
                }
            }
            level = next;
        }
        Some(level[0])
    }
}

/// 关系日志环
pub struct LogRing {
    pub anchor: [u8; HASH_LEN],
    pub entries: Vec<LogEntry>,
    genesis: [u8; HASH_LEN],
}

impl LogRing {
    pub fn new(anchor_seed: &[u8]) -> Self {
        let genesis = sha256(anchor_seed);
        Self {
            anchor: genesis,
            entries: Vec::new(),
            genesis,
        }
    }

    /// append 一条新记录 (自动链上 hash)
    pub fn append(&mut self, kind: u32, payload: &[u8], ts_us: u64) -> &LogEntry {
        let prev_hash = self.last_hash();
        let seq = self.entries.len() as u64;
        let e = LogEntry::new(seq, kind, payload, ts_us, prev_hash);
        self.entries.push(e);
        &self.entries[self.entries.len() - 1]
    }

    /// 最后一条 hash (genesis 若为空)
    pub fn last_hash(&self) -> [u8; HASH_LEN] {
        match self.entries.last() {
            Some(e) => e.hash,
            None => self.genesis,
        }
    }

    /// 验链完整性
    pub fn verify(&self) -> bool {
        let mut prev = self.genesis;
        for e in &self.entries {
            if e.prev_hash != prev { return false; }
            if e.hash != e._compute_hash() { return false; }
            prev = e.hash;
        }
        true
    }

    /// Merkle 当前 root
    pub fn merkle_root(&self) -> [u8; HASH_LEN] {
        if self.entries.is_empty() { return self.genesis; }
        let hashes: Vec<[u8; HASH_LEN]> = self.entries.iter()
            .map(|e| e.hash)
            .collect();
        MerkleTree::root_from(&hashes).unwrap_or(self.genesis)
    }

    /// 按 kind 筛选
    pub fn filter(&self, kind: u32) -> Vec<&LogEntry> {
        self.entries.iter().filter(|e| e.kind == kind).collect()
    }

    /// 快照 (只含 hash 用于跨节点同步)
    pub fn snapshot_hashes(&self) -> Vec<[u8; HASH_LEN]> {
        std::iter::once(self.genesis)
            .chain(self.entries.iter().map(|e| e.hash))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chain_integrity() {
        let mut ring = LogRing::new(b"test-anchor");
        ring.append(1, b"line1", 1000);
        ring.append(2, b"line2", 2000);
        ring.append(3, b"line3", 3000);
        assert!(ring.verify());
        assert_eq!(ring.entries.len(), 3);
    }

    #[test]
    fn tamper_detected() {
        let mut ring = LogRing::new(b"test-anchor");
        ring.append(1, b"a", 1000);
        ring.append(2, b"b", 2000);
        // 篡改 [0] 的 payload 而不重算 hash
        ring.entries[0].payload = vec![0xFF, 0xFF];
        assert!(!ring.verify());
    }

    #[test]
    fn merkle_root_changes() {
        let mut ring = LogRing::new(b"seed");
        let r1 = ring.merkle_root();
        ring.append(1, b"x", 1000);
        let r2 = ring.merkle_root();
        assert_ne!(r1, r2);
    }

    #[test]
    fn filter_by_kind() {
        let mut ring = LogRing::new(b"seed");
        ring.append(10, b"a", 1000);
        ring.append(20, b"b", 2000);
        ring.append(10, b"c", 3000);
        assert_eq!(ring.filter(10).len(), 2);
        assert_eq!(ring.filter(20).len(), 1);
    }
}
