"""Execute actual firmware admission functions with mocked radio/RTC hardware."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def function(path, signature):
    text = (ROOT / path).read_text()
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

class ClockPriority(unittest.TestCase):
    def test_admission_and_no_side_effects_on_rejection(self):
        compiler = shutil.which('g++') or 'C:/Qt/Tools/mingw1310_64/bin/g++.exe'
        source = r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include "r3_time_beacon.h"
#define portENTER_CRITICAL(x) ((void)0)
#define portEXIT_CRITICAL(x) ((void)0)
struct {bool canboxMode=false, connected=true, utcValid=true;uint64_t receiveUs=100;} status;
std::atomic<bool> linkUp(true),authenticated(true);
uint64_t now=200;
uint64_t esp_timer_get_time(){return now;}
namespace recorder {bool active=false;bool busy(){return active;}}
bool trustedUtc=true;unsigned clockRevision=0,writes=0,forgot=0;
void ecosystemForgetClockEvidence(){++forgot;}
bool setRtcUtc(uint64_t){++writes;return true;}
'''
        source += function('firmware/src/r3_ble_client.cpp', 'bool r3BleTimeAuthorityAvailable()')
        source += '\n' + function('firmware/src/rtc_test.cpp', 'bool panelSetRtcUtc(')
        source += r'''
int main(){
 assert(r3BleTimeAuthorityAvailable());
 assert(!panelSetRtcUtc(1800000000,false));assert(writes==0&&forgot==0&&trustedUtc);
 assert(panelSetRtcUtc(1800000000,true));assert(writes==1&&forgot==1);
 recorder::active=true;
 assert(!panelSetRtcUtc(1800000000,true));assert(writes==1);recorder::active=false;
 now=status.receiveUs+r3_time::kStaleAfterUs;
 assert(!r3BleTimeAuthorityAvailable());assert(panelSetRtcUtc(1800000000,false));
 now=status.receiveUs+r3_time::kStaleAfterUs-1;assert(r3BleTimeAuthorityAvailable());
 authenticated=false;assert(!r3BleTimeAuthorityAvailable());authenticated=true;
 linkUp=false;assert(!r3BleTimeAuthorityAvailable());linkUp=true;
 status.utcValid=false;assert(!r3BleTimeAuthorityAvailable());status.utcValid=true;
 status.canboxMode=true;assert(!r3BleTimeAuthorityAvailable());status.canboxMode=false;
 now=status.receiveUs-1;assert(!r3BleTimeAuthorityAvailable());
 assert(!panelSetRtcUtc(946684799,false));assert(!panelSetRtcUtc(4102444799ULL,false));
 assert(writes==2&&forgot==2);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = Path(tmp)/'clock.cpp', Path(tmp)/'clock.exe'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++11','-static','-Ifirmware/include',str(cpp),'-o',str(exe)],cwd=ROOT,check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
