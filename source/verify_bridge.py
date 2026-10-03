"""Execute the compiled bridge in Unicorn with mocked Win32/Steam backends.
This checks the shipped x86/x64 ABI and routing, not live Steam IPC or game compatibility.
"""
from pathlib import Path
import struct, pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

class Harness:
 def __init__(self,bits):
  self.bits=bits;self.sz=bits//8;self.uc=Uc(UC_ARCH_X86,UC_MODE_64 if bits==64 else UC_MODE_32)
  self.pc=UC_X86_REG_RIP if bits==64 else UC_X86_REG_EIP;self.sp=UC_X86_REG_RSP if bits==64 else UC_X86_REG_ESP;self.ax=UC_X86_REG_RAX if bits==64 else UC_X86_REG_EAX
  self.cx=UC_X86_REG_RCX if bits==64 else UC_X86_REG_ECX
  n='steam_api64' if bits==64 else 'steam_api';self.pe=pefile.PE(str(Path(__file__).parents[1]/('payload%d'%bits)/(n+'.dll')));self.base=self.pe.OPTIONAL_HEADER.ImageBase
  self.uc.mem_map(self.base,(self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095);self.uc.mem_write(self.base,self.pe.get_memory_mapped_image())
  for a,s in [(0x30000000,0x100000),(0x40000000,0x100000),(0x60000000,0x1000000),(0x70000000,0x100000)]:self.uc.mem_map(a,s)
  self.heap=0x60000000;self.stub=0x30000000;self.stop=0x300ff000;self.hooks={};self.raw=0x40005000;self.table=0x40006000;self.factory=0x40001000;self.head=0x40003000;self.node=0x40004000
  self.writeptr(self.raw,self.table);self.writeptr(self.head,self.node)
  if bits==64:self.uc.mem_write(self.factory,b'\x4c\x8b\x0d'+struct.pack('<i',self.head-self.factory-7)+b'\x4c\x8b\xd2\x4c\x8b\xd9')
  else:self.uc.mem_write(self.factory,b'\x55\x8b\xec\x56\x8b\x35'+struct.pack('<I',self.head))
  self.hooks[self.factory]=('factory',2,False)
  self.origcreate=self.addhook('origcreate',1,False);self.originit=self.addhook('originit',2,False)
  self.rawgeneric=self.addhook('rawgeneric',3,True);self.writeptr(self.table+12*self.sz,self.rawgeneric)
  self.raw_if={};self.seen=[]
  for kind,version,count in [(1,'SteamFriends017',80),(2,'STEAMAPPS_INTERFACE_VERSION008',33),(3,'STEAMUGC_INTERFACE_VERSION020',94),(4,'STEAMREMOTEPLAY_INTERFACE_VERSION002',8)]:
   obj=self.alloc(self.sz);vt=self.alloc(count*self.sz);self.writeptr(obj,vt);self.raw_if[version]=obj
   for i in range(count):self.writeptr(vt+i*self.sz,self.addhook('method:%d:%d'%(kind,i),0,True))
  for i in range(40):
   if i!=12:self.writeptr(self.table+i*self.sz,self.addhook('client:%d'%i,0,True))
  for d in self.pe.DIRECTORY_ENTRY_IMPORT:
   for imp in d.imports:
    name=imp.name.decode();argc={'GetModuleFileNameA':3,'GetProcAddress':2,'LoadLibraryExA':3,'GetModuleHandleA':1,'HeapAlloc':3,'HeapFree':3,'VirtualAlloc':4,'VirtualProtect':4,'VirtualQuery':3,'VirtualFree':3,'FlushInstructionCache':3,'CreateFileA':7,'WriteFile':5,'CloseHandle':1,'InitializeCriticalSection':1,'EnterCriticalSection':1,'LeaveCriticalSection':1,'DisableThreadLibraryCalls':1,'wvsprintfA':3}.get(name,0)
    self.writeptr(imp.address,self.addhook(name,argc,False,winapi=True))
  self.exports={e.name.decode():self.base+e.address for e in self.pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name and not e.forwarder}
  self.uc.hook_add(UC_HOOK_CODE,self.code)
 def alloc(self,n):
  a=self.heap;self.heap+=(n+31)&~31;return a
 def string(self,s):
  a=self.alloc(len(s)+1);self.uc.mem_write(a,s.encode()+b'\0');return a
 def readstr(self,a):
  if not a:return ''
  out=bytearray()
  while len(out)<2048:
   b=self.uc.mem_read(a+len(out),1)[0]
   if not b:return out.decode()
   out.append(b)
  raise AssertionError('unterminated string')
 def writeptr(self,a,p):self.uc.mem_write(a,int(p).to_bytes(self.sz,'little'))
 def readptr(self,a):return int.from_bytes(self.uc.mem_read(a,self.sz),'little')
 def addhook(self,name,argc,this,winapi=False):
  a=self.stub;self.stub+=16;self.hooks[a]=(name,argc,this,winapi);return a
 def args(self,n,this=False):
  sp=self.uc.reg_read(self.sp)
  if self.bits==64:
   regs=[UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9];args=[self.uc.reg_read(r) for r in regs]
   args += [self.readptr(sp+0x28+i*8) for i in range(max(0,n+int(this)-4))]
   return args[int(this):n+int(this)]
  return [self.readptr(sp+4+i*4) for i in range(n)]
 def ret(self,result,cleanup):
  sp=self.uc.reg_read(self.sp);ret=self.readptr(sp);self.uc.reg_write(self.ax,result);self.uc.reg_write(self.sp,sp+self.sz+(cleanup if self.bits==32 else 0));self.uc.reg_write(self.pc,ret)
 def code(self,uc,address,size,user):
  if address==self.stop:uc.emu_stop();return
  if address not in self.hooks:return
  h=self.hooks[address];name,n,this=h[:3];winapi=len(h)>3 and h[3];a=self.args(n,this);cleanup=4*n if this or winapi else 0;r=0
  if name in ('factory','origcreate'):
   version=self.readstr(a[0])
   registry=self.readptr(self.head)
   while registry and registry!=self.node:
    if self.readstr(self.readptr(registry+self.sz))==version:
     uc.reg_write(self.pc,self.readptr(registry));return
    registry=self.readptr(registry+2*self.sz)
   if version in ['SteamClient021','SteamClient017']:r=self.raw
  elif name=='originit':
   actual=[];at=a[0]
   while at and self.readstr(at):
    v=self.readstr(at);actual.append(v);at+=len(v)+1
   assert actual==['STEAMAPPS_INTERFACE_VERSION008','SteamFriends017','STEAMUGC_INTERFACE_VERSION020','STEAMREMOTEPLAY_INTERFACE_VERSION002','SteamUser023'],actual
   r=0
  elif name=='GetModuleFileNameA':
   path='C:\\GarrysMod\\GMod-LegacySteam-Test1\\payload\\steam_api.dll' if a[0] else 'C:\\GarrysMod\\gmod.exe'
   uc.mem_write(a[1],path.encode()+b'\0');r=len(path)
  elif name=='GetModuleHandleA':r=0x40000000
  elif name=='LoadLibraryExA':r=0x42000000
  elif name=='GetProcAddress':
   export=self.readstr(a[1]);r={'CreateInterface':self.factory,'SteamInternal_CreateInterface':self.origcreate,'SteamInternal_SteamAPI_Init':self.originit}.get(export,0)
  elif name=='GetProcessHeap':r=1
  elif name in ('HeapAlloc','VirtualAlloc'):r=self.alloc(a[2] if name=='HeapAlloc' else a[1])
  elif name=='VirtualProtect':uc.mem_write(a[3],struct.pack('<I',4));r=1
  elif name=='VirtualQuery':
   buf=bytearray(48 if self.bits==64 else 28);struct.pack_into('<I',buf,32 if self.bits==64 else 16,0x1000);uc.mem_write(a[1],bytes(buf));r=len(buf)
  elif name=='CreateFileA':r=(1<<self.bits)-1
  elif name=='wvsprintfA':uc.mem_write(a[0],b'\0');r=0
  elif name=='rawgeneric':
   assert uc.reg_read(self.cx)==self.raw
   self.seen.append(('query',self.readstr(a[2]),a[:2]));r=self.raw_if.get(self.readstr(a[2]),0)
  elif name.startswith('method:'):
   kind,index=map(int,name.split(':')[1:]);orig=list(self.raw_if.values())[kind-1];assert uc.reg_read(self.cx)==orig,(name,hex(uc.reg_read(self.cx)),hex(orig))
   if kind==3 and index==75:n=2;cleanup=8;self.seen.append(('items',self.args(2,True)))
   elif kind==4 and index==6:n=1;cleanup=4;assert self.args(1,True)[0]==1
   elif kind==4 and index in [1,2,3,4]:n=1;cleanup=4
   self.seen.append((kind,index));r=0x1200+index
  elif name.startswith('client:'):assert uc.reg_read(self.cx)==self.raw;r=0x100+int(name.split(':')[1])
  else:r=1
  self.ret(r,cleanup)
 def call(self,addr,args=[],this=None,cleanup=0):
  sp=0x700ff000-(8 if self.bits==64 else 4);self.uc.reg_write(self.sp,sp);self.writeptr(sp,self.stop)
  if self.bits==64:
   a=([this] if this is not None else [])+list(args);regs=[UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9]
   for i,r in enumerate(regs):self.uc.reg_write(r,a[i] if i<len(a) else 0)
   for i,x in enumerate(a[4:]):self.writeptr(sp+0x28+i*8,x)
  else:
   if this is not None:self.uc.reg_write(self.cx,this)
   for i,x in enumerate(args):self.writeptr(sp+4+i*4,x)
  self.uc.emu_start(addr,self.stop+1,count=1000000)
  assert self.uc.reg_read(self.pc)==self.stop,'did not return'
  expected=sp+self.sz+(cleanup if self.bits==32 else 0)
  assert self.uc.reg_read(self.sp)==expected,('stack imbalance',hex(addr),hex(self.uc.reg_read(self.sp)),hex(expected))
  return self.uc.reg_read(self.ax)
 def method(self,obj,slot,args=[],cleanup=0):return self.call(self.readptr(self.readptr(obj)+slot*self.sz),args,obj,cleanup)
 def run(self):
  self.call(self.base+self.pe.OPTIONAL_HEADER.AddressOfEntryPoint,[self.base,1,0],cleanup=12)
  error=self.alloc(1024);assert self.call(self.exports['SteamInternal_SteamAPI_Init'],[self.string('STEAMAPPS_INTERFACE_VERSION009\0SteamFriends018\0STEAMUGC_INTERFACE_VERSION021\0STEAMREMOTEPLAY_INTERFACE_VERSION004\0SteamUser023\0'),error])==0
  client=self.call(self.exports['SteamInternal_CreateInterface'],[self.string('SteamClient023')]);assert client and client!=self.raw
  assert self.method(client,20)==0x100+21 # shifted client slot
  names=['SteamFriends018','STEAMAPPS_INTERFACE_VERSION009','STEAMUGC_INTERFACE_VERSION021','STEAMREMOTEPLAY_INTERFACE_VERSION004'];objects=[]
  for name in names:
   obj=self.method(client,12,[7,8,self.string(name)],cleanup=12);assert obj;objects.append(obj)
  friends,apps,ugc,remote=objects
  core=self.call(self.exports['SteamInternal_CreateInterface'],[self.string('SteamClient017')]);assert core and core!=self.raw
  for name,obj in zip(names,objects):assert self.method(core,12,[7,8,self.string(name)],cleanup=12)==obj
  assert self.method(core,30)==0x100+30
  assert self.method(friends,1)==0x1202 # removed SetPersonaName
  import re
  mapping=list(map(int,re.findall(r'\d+',Path(__file__).with_name('friends_map.h').read_text().split('{')[1])))
  for slot,target in enumerate(mapping):assert self.method(friends,slot)==0x1200+target
  for slot,name in [(8,names[0]),(15,names[1]),(25,names[2]),(36,names[3])]:
   assert self.method(client,slot,[7,8,self.string(name)],cleanup=12)==objects[names.index(name)]
  assert self.method(apps,23)==0x1217
  assert self.method(ugc,74,[1],cleanup=4)==0x124a
  ids=self.alloc(64);assert self.method(ugc,75,[ids,8,1],cleanup=12)==0x124b
  assert ('items',[ids,8]) in self.seen
  assert self.method(ugc,94,[ids,8,1],cleanup=12)==0
  assert self.method(ugc,95,[ids,8],cleanup=8)==0
  assert self.method(ugc,96,[7,0] if self.bits==32 else [7],cleanup=8)==0
  assert self.method(ugc,97)==0
  assert self.method(ugc,98,[ids,8],cleanup=8)==0
  avail=self.alloc(4);priv=self.alloc(4);assert self.method(apps,30,[avail,priv],cleanup=8)==0
  assert self.method(apps,31,[0,avail,priv,ids,16,ids,16,avail],cleanup=32)==0
  assert self.method(apps,32,[ids],cleanup=4)==0
  self.method(apps,33,[0],cleanup=4);self.method(apps,34,[800,600],cleanup=8)
  assert self.method(remote,3,[88],cleanup=4)==0x1202
  assert self.method(remote,11)==(0x1206&255)
  assert self.method(remote,15,[ids,8],cleanup=8)==0
  assert self.method(remote,5,[1],cleanup=4)==0xffffffff
  self.method(remote,14);self.method(remote,16,[1,1],cleanup=8)
  self.method(remote,17,[1,0,0],cleanup=12)
  assert self.method(remote,18,[1,1,0,0,ids,4],cleanup=24)==0
  self.method(remote,19,[1,0],cleanup=8)
  print('%d-bit compiled bridge: setup, registry, client/friends slot remapping, UGC argument adaptation, unsupported methods, export ABI and stack checks PASS'%self.bits)

if __name__=='__main__':
 for bits in [32,64]:Harness(bits).run()
