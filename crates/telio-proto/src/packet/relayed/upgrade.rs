use std::net::SocketAddr;

use crate::{
    messages::upgrade::*, Codec, CodecError, CodecResult, DowncastPacket, PacketRelayed,
    PacketTypeRelayed, MAX_PACKET_SIZE,
};

use bytes::BufMut;
use protobuf::Message;

/// Packet encapsulating ugprade message
#[derive(Debug, PartialEq, Eq, Clone)]
pub struct UpgradeMsg {
    /// Endpoint which message sender is requesting to upgrade to
    pub endpoint: SocketAddr,
}

impl Codec<PacketTypeRelayed> for UpgradeMsg {
    const TYPES: &'static [PacketTypeRelayed] = &[PacketTypeRelayed::Upgrade];

    fn decode(bytes: &[u8]) -> CodecResult<Self>
    where
        Self: Sized,
    {
        if bytes.is_empty() {
            return Err(CodecError::InvalidLength);
        }

        match PacketTypeRelayed::from(*bytes.first().unwrap_or(&(PacketTypeRelayed::Invalid as u8)))
        {
            PacketTypeRelayed::Upgrade => {
                let proto_upgrade =
                    Upgrade::parse_from_bytes(bytes.get(1..).ok_or(CodecError::DecodeFailed)?)
                        .map_err(|_| CodecError::DecodeFailed)?;
                let endpoint: SocketAddr = proto_upgrade
                    .get_endpoint()
                    .parse()
                    .map_err(|_| CodecError::DecodeFailed)?;
                Ok(Self { endpoint })
            }
            _ => Err(CodecError::DecodeFailed),
        }
    }

    fn encode(self) -> CodecResult<Vec<u8>> {
        let mut bytes = Vec::with_capacity(MAX_PACKET_SIZE);
        let mut msg = Upgrade::new();
        msg.set_endpoint(self.endpoint.to_string());

        bytes.put_u8(PacketTypeRelayed::Upgrade as u8);
        msg.write_to_vec(&mut bytes)
            .map_err(|_| CodecError::Encode)?;

        Ok(bytes)
    }

    fn packet_type(&self) -> PacketTypeRelayed {
        PacketTypeRelayed::Upgrade
    }
}

impl DowncastPacket<PacketRelayed> for UpgradeMsg {
    fn downcast(packet: PacketRelayed) -> Result<Self, PacketRelayed>
    where
        Self: Sized,
    {
        match packet {
            PacketRelayed::Upgrade(upgrade) => Ok(upgrade),
            packet => Err(packet),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_packet() {
        let upgrade_bytes = &[
            8, 10, 14, 49, 50, 55, 46, 48, 46, 48, 46, 49, 58, 49, 50, 51, 52,
        ];
        let upgrade_msg = UpgradeMsg::decode(upgrade_bytes).expect("Failed to parse upgrade msg");
        assert_eq!(upgrade_msg.endpoint, "127.0.0.1:1234".parse().unwrap());
    }

    #[test]
    fn fail_to_decode_small_packet() {
        let bytes = &[6];
        let data = UpgradeMsg::decode(bytes);
        assert_eq!(data, Err(CodecError::DecodeFailed));
    }

    #[test]
    fn fail_to_decode_packet_of_wrong_type() {
        let bytes = &[PacketTypeRelayed::Invalid as u8];
        let data = UpgradeMsg::decode(bytes);
        assert_eq!(data, Err(CodecError::DecodeFailed));
    }

    #[test]
    fn encode_packet() {
        let upgrade_msg = UpgradeMsg {
            endpoint: "127.0.0.1:1234".parse().unwrap(),
        };
        let expected_upgrade_bytes: &[u8] = &[
            8, 10, 14, 49, 50, 55, 46, 48, 46, 48, 46, 49, 58, 49, 50, 51, 52,
        ];
        let actual_upgrade_bytes = upgrade_msg.encode().unwrap();
        assert_eq!(expected_upgrade_bytes, actual_upgrade_bytes);
    }
}
