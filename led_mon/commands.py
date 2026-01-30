# https://github.com/FrameworkComputer/inputmodule-rs/blob/main/commands.md

# Display is 9x34 wide x tall
class Commands():
    Brightness 	 = 0x00
    Pattern 	 = 0x01
    Bootloader 	 = 0x02
    Sleep 	     = 0x03
    GetSleep 	 = 0x03
    Animate 	 = 0x04
    GetAnimate 	 = 0x04
    Panic 	     = 0x05
    DrawBW 	     = 0x06
    StageCol 	 = 0x07
    FlushCols 	 = 0x08
    SetText 	 = 0x09
    StartGame 	 = 0x10
    GameCtrl 	 = 0x11
    GameStatus 	 = 0x12
    SetColor 	 = 0x13
    DisplayOn 	 = 0x14
    InvertScreen = 0x15
    SetPxCol 	 = 0x16
    FlushFB 	 = 0x17
    Version 	 = 0x20


def send_command(s, command_id, parameters = None, with_response=False):
    message = bytearray([0x32, 0xAC, command_id])
    if parameters:
        message.extend(parameters)
    s.write(message)
    if with_response:
        res = s.read(1)
        return res
    
def do_animate(s, animate=False, with_response=False):
    message = bytearray([0x32, 0xAC, Commands.Animate, animate])
    s.write(message)
    if with_response:
        res = s.read(1)
        return res
