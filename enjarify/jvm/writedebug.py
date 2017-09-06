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

from ..byteio import Writer
from .. import debug

class LineNumberTableEntry:
    def __init__(self, start_pc, line_number):
        self.start_pc = start_pc
        self.line_number = line_number

class LocalVariableTableEntry:
    def __init__(self, start_pc, length, name, descriptor, index):
        self.start_pc = start_pc
        self.length = length
        self.name = name
        self.descriptor = descriptor
        self.index = index

class LocalVariableTypeTableEntry:
    def __init__(self, start_pc, length, name, signature, index):
        self.start_pc = start_pc
        self.length = length
        self.name = name
        self.signature = signature
        self.index = index

def translateAddr(addr, pos_map):
    if addr < len(pos_map):
        return pos_map[addr]
    else:
#        print("Debug info referenced dalvik instruction", str(addr), 
#          "which was removed during optimization. Using instruction number " + str(len(pos_map) - 1) + " instead.")
        return len(pos_map) - 1

def endVariableAt(index, addr, tables, implicit=False):
    found = 0
    for entry in tables:
        if entry.index == index and entry.start_pc <= addr <= entry.start_pc + entry.length:
            entry.length = addr - entry.start_pc
            found += 1
#            if implicit:
#                print("    Ended", entry.descriptor.decode("utf-8") if isinstance(entry, LocalVariableTableEntry) 
#                  else entry.signature.decode("utf-8"), entry.name.decode("utf-8"), "implicitly")
    return found

class RegisterInfo:
    def __init__(self, name, type, sig):
        self.name = name
        self.type = type
        self.sig = sig

def makeDebugTables(pool, irdata, pos_map, bytecode_len, regmap): # TODO: move in writeir?
    method_name = irdata.method.id.name.decode("utf-8")
#    print("Translating debug info for method", method_name)
    debug_info = irdata.method.code.debug_info
    line_number_table = []
    local_variable_table = []
    local_variable_type_table = []
    
    line = debug_info.line_start
    addr = 0
    last_local = {}
    for inst in debug_info.bytecode:
        if inst.opcode == debug.DBG_END_SEQUENCE:
            break
        
        elif inst.opcode == debug.DBG_ADVANCE_PC:
            addr += inst.addr_diff
        
        elif inst.opcode == debug.DBG_ADVANCE_LINE:
            line += inst.line_diff
        
        elif inst.opcode == debug.DBG_START_LOCAL:
            taddr = translateAddr(addr, pos_map)
#            print("  DBG_START_LOCAL", inst.type.decode("utf-8"), inst.name.decode("utf-8"), 
#              "(addr=" + str(addr), "taddr=" + str(taddr), "line=" + str(line) + ")")
            found = False
            for k, index in regmap.items():
                if(k[0] == inst.register_num):
                    endVariableAt(index, taddr, local_variable_table + local_variable_type_table, True)
                    local_variable_table.append(LocalVariableTableEntry(taddr, bytecode_len - taddr, inst.name, inst.type, index))
                    found = True
            if not found:
                print("Register", inst.register_num, "in", method_name, "doesn't exist but had local variable info:", taddr, inst.type, inst.name)
            last_local[inst.register_num] = RegisterInfo(inst.name, inst.type, None)
        
        elif inst.opcode == debug.DBG_START_LOCAL_EXTENDED:
            taddr = translateAddr(addr, pos_map)
#            print("  DBG_START_LOCAL_EXTENDED", inst.type.decode("utf-8") if inst.type is not None else None, 
#              "(sig=" + inst.sig.decode("utf-8") if inst.sig is not None else None + ")", inst.name.decode("utf-8"),
#              "(addr=" + str(addr), "taddr=" + str(taddr), "line=" + str(line) + ")")
            found = 0
            for k, index in regmap.items():
                if(k[0] == inst.register_num):
                    endVariableAt(index, taddr, local_variable_table + local_variable_type_table, True)
                    if inst.type is not None or inst.type is None and inst.sig is None:
                        entry = LocalVariableTableEntry(taddr, bytecode_len - taddr, inst.name, inst.type, index)
                        local_variable_table.append(entry)
                    if inst.sig is not None:
                        entry = LocalVariableTypeTableEntry(taddr, bytecode_len - taddr, inst.name, inst.sig, index)
                        local_variable_type_table.append(entry)
                    found += 1
            if not found:
                print("Register", inst.register_num, "in", method_name, "doesn't exist but had extended local variable info:", taddr, inst.sig, inst.name)
            last_local[inst.register_num] = RegisterInfo(inst.name, inst.type, inst.sig)
        
        elif inst.opcode == debug.DBG_END_LOCAL:
            taddr = translateAddr(addr, pos_map)
#            print("  DBG_END_LOCAL", inst.register_num, "(addr=" + str(addr), "taddr=" + str(taddr), "line=" + str(line) + ")")
            found = 0
            for k, index in regmap.items():
                if(k[0] == inst.register_num):
                    found += endVariableAt(index, taddr, local_variable_table + local_variable_type_table)
#            if not found:
#                print("Tried to end non-existing local register_num =", inst.register_num) # Why is this happening?
        
        elif inst.opcode == debug.DBG_RESTART_LOCAL:
#            taddr = translateAddr(addr, pos_map)
#            print("  DBG_RESTART_LOCAL", inst.register_num, "(addr=" + str(addr), "taddr=" 
#              + str(taddr), "line=" + str(line), "last_local=" + str(last_local) + ")")
            if inst.register_num in last_local:
                taddr = translateAddr(addr, pos_map)
                info = last_local[inst.register_num]
                for k, index in regmap.items():
                    if(k[0] == inst.register_num):
                        if endVariableAt(index, taddr, local_variable_table + local_variable_type_table):
                            pass
#                            print("    Restarting still existing variable!") # Why is this happening?
                    if info.type is not None or info.type is None and info.sig is None:
                        entry = LocalVariableTableEntry(taddr, bytecode_len - taddr, info.name, info.type, index)
                        local_variable_table.append(entry)
                    if info.sig is not None:
                        entry = LocalVariableTypeTableEntry(taddr, bytecode_len - taddr, info.name, info.sig, index)
                        local_variable_type_table.append(entry)
#            else:
#                print("Tried to restart local register_num =", inst.register_num,"but no previous entry in that register!") # Why is this happening?
        
        elif inst.opcode == debug.DBG_SET_FILE:
            #taddr = translateAddr(addr, pos_map)
            #print("  DBG_RESTART_LOCAL", inst.name.decode("utf-8"), "(addr=" + str(addr), "taddr=" + str(taddr), "line=" + str(line) + ")")
            print("Can't translate DBG_SET_FILE in method", irdata.method.id.name.decode("utf-8"), ", no JVM equivalent!")
        
        elif inst.opcode >= debug.DBG_FIRST_SPECIAL:
            adjusted_opcode = inst.opcode - debug.DBG_FIRST_SPECIAL
            line += -4 + (adjusted_opcode % 15)
            addr += adjusted_opcode // 15
            entry = LineNumberTableEntry(translateAddr(addr, pos_map), line)
            line_number_table.append(entry)
    
    if not len(line_number_table):
        line_number_table = None
    if not len(local_variable_table):
        local_variable_table = None
    if not len(local_variable_type_table):
        local_variable_type_table = None
    return line_number_table, local_variable_table, local_variable_type_table

def writeDebugAttributes(pool, irdata, pos_map, bytecode_len, regmap):
    stream = Writer()
    attr_count = 0
    line_number_table, local_variable_table, local_variable_type_table = makeDebugTables(pool, irdata, pos_map, bytecode_len, regmap)
    
    if line_number_table is not None:
        attr_count += 1
        stream.u16(pool.utf8(b"LineNumberTable"))
        stream.u32(2 + len(line_number_table) * 4) # attribute length
        stream.u16(len(line_number_table))
#        print("LNT for", irdata.method.id.name, "has", len(line_number_table), "entries: ")
        for entry in line_number_table:
#            print("  start_pc:", entry.start_pc, "line_number:", entry.line_number)
            stream.u16(entry.start_pc)
            stream.u16(entry.line_number)
    
    if local_variable_table is not None:
        attr_count += 1
        stream.u16(pool.utf8(b"LocalVariableTable"))
        stream.u32(2 + len(local_variable_table) * 10) # attribute length
        stream.u16(len(local_variable_table))
        for entry in local_variable_table:
            stream.u16(entry.start_pc)
            stream.u16(entry.length)
            stream.u16(pool.utf8(entry.name))
            stream.u16(pool.utf8(entry.descriptor))
            stream.u16(entry.index)
    
    if local_variable_type_table is not None:
        attr_count += 1
        stream.u16(pool.utf8(b"LocalVariableTypeTable"))
        stream.u32(2 + len(local_variable_type_table) * 10) # attribute length
        stream.u16(len(local_variable_type_table))
        for entry in local_variable_type_table:
            stream.u16(entry.start_pc)
            stream.u16(entry.length)
            stream.u16(pool.utf8(entry.name))
            stream.u16(pool.utf8(entry.signature))
            stream.u16(entry.index)
    
    return attr_count, stream.toBytes()
