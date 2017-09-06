# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DBG_END_SEQUENCE = 0x00
DBG_ADVANCE_PC = 0x01
DBG_ADVANCE_LINE = 0x02
DBG_START_LOCAL = 0x03
DBG_START_LOCAL_EXTENDED = 0x04
DBG_END_LOCAL = 0x05
DBG_RESTART_LOCAL = 0x06
DBG_SET_PROLOGUE_END = 0x07
DBG_SET_EPILOGUE_BEGIN = 0x08
DBG_SET_FILE = 0x09
DBG_FIRST_SPECIAL = 0x0A

class DebugInstruction:
    def __init__(self, dex, stream):
        self.opcode = stream.u8()
        if self.opcode == DBG_ADVANCE_PC:
          self.addr_diff = stream.uleb128()
        elif self.opcode == DBG_ADVANCE_LINE:
          self.line_diff = stream.sleb128()
        elif self.opcode == DBG_START_LOCAL:
          self.register_num = stream.uleb128()
          self.name_idx = stream.uleb128p1()
          self.type_idx = stream.uleb128p1()
          
          self.name = dex.string(self.name_idx)
          self.type = dex.type(self.type_idx)
        elif self.opcode == DBG_START_LOCAL_EXTENDED:
          self.register_num = stream.uleb128()
          self.name_idx = stream.uleb128p1()
          self.type_idx = stream.uleb128p1()
          self.sig_idx = stream.uleb128p1()
          
          self.name = dex.string(self.name_idx)
          self.type = dex.type(self.type_idx)
          self.sig = dex.string(self.sig_idx)
        elif self.opcode == DBG_END_LOCAL:
          self.register_num = stream.uleb128()
        elif self.opcode == DBG_RESTART_LOCAL:
          self.register_num = stream.uleb128()
        elif self.opcode == DBG_SET_FILE:
          self.name_idx = stream.uleb128p1()
          
          self.name = dex.string(self.name_idx)

def parseDebugInfo(dex, stream):
    ops = []
    while 1:
        op = DebugInstruction(dex, stream)
        ops.append(op)
        if op.opcode == DBG_END_SEQUENCE:
          break
    return ops
