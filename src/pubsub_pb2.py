# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: pubsub.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0cpubsub.proto\x12\x06pubsub\"\x17\n\x04Pong\x12\x0f\n\x07message\x18\x01 \x01(\t\"+\n\x07Message\x12\x0f\n\x07\x63hannel\x18\x01 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x02 \x01(\t\"\x17\n\x07\x43hannel\x12\x0c\n\x04name\x18\x01 \x01(\t\"0\n\x0b\x43hannelList\x12!\n\x08\x63hannels\x18\x01 \x03(\x0b\x32\x0f.pubsub.Channel\"\x07\n\x05\x45mpty\"\x16\n\x03\x41\x63k\x12\x0f\n\x07success\x18\x01 \x01(\x08\x32\x9c\x01\n\x06PubSub\x12)\n\x07Publish\x12\x0f.pubsub.Message\x1a\x0b.pubsub.Ack\"\x00\x12\x31\n\tSubscribe\x12\x0f.pubsub.Channel\x1a\x0f.pubsub.Message\"\x00\x30\x01\x12\x34\n\x0cListChannels\x12\r.pubsub.Empty\x1a\x13.pubsub.ChannelList\"\x00\x32/\n\x06Health\x12%\n\x04Ping\x12\r.pubsub.Empty\x1a\x0c.pubsub.Pong\"\x00\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pubsub_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_PONG']._serialized_start=24
  _globals['_PONG']._serialized_end=47
  _globals['_MESSAGE']._serialized_start=49
  _globals['_MESSAGE']._serialized_end=92
  _globals['_CHANNEL']._serialized_start=94
  _globals['_CHANNEL']._serialized_end=117
  _globals['_CHANNELLIST']._serialized_start=119
  _globals['_CHANNELLIST']._serialized_end=167
  _globals['_EMPTY']._serialized_start=169
  _globals['_EMPTY']._serialized_end=176
  _globals['_ACK']._serialized_start=178
  _globals['_ACK']._serialized_end=200
  _globals['_PUBSUB']._serialized_start=203
  _globals['_PUBSUB']._serialized_end=359
  _globals['_HEALTH']._serialized_start=361
  _globals['_HEALTH']._serialized_end=408
# @@protoc_insertion_point(module_scope)
