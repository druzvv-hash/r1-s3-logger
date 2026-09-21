#include "ota_update.h"
#include "sd_files.h"
#include "recorder.h"
#include "ina228_test.h"
#include "ecosystem_owner.h"
#include <Arduino.h>
#include <WebServer.h>
#include <Update.h>
#include <esp_ota_ops.h>
#include <atomic>

namespace {
// Owner alone holds/releases the SD gate and pauses/resumes acquisition.
std::atomic<int> maintenance{0}; // 0 idle, 1 requested, 2 held, 3 denied
bool writing=false, complete=false;
size_t expected=0, received=0;
uint32_t touched=0, rebootAt=0;
String failure;
void abortUpload(const char* why){
    if(Update.isRunning())Update.abort();
    writing=false;complete=false;failure=why;maintenance.store(0);
}
bool reserve(){
    maintenance.store(1);
    const uint32_t began=millis();
    while(maintenance.load()==1 && millis()-began<2500)delay(5);
    if(maintenance.load()==2)return true;
    maintenance.store(0);return false;
}
const char PAGE[]=R"HTML(<!doctype html><html lang="uk"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>R1 OTA</title>
<style>body{font:18px system-ui;background:#10171c;color:#e2edef;max-width:650px;margin:40px auto;padding:20px}button,input{font:inherit;margin:15px 0;max-width:100%}a{color:#9de0c5}</style>
<h1>Оновлення R1 через Wi-Fi</h1><p>Завершіть запис. Виберіть лише <b>firmware.bin для R1-S3</b> із середовища esp32-s3-usb. Не bootloader, partitions або об'єднаний образ.</p><p>Під час оновлення не вимикайте живлення. Показники тимчасово призупиняться. Налаштування та записи залишаться.</p>
<input id="file" type="file" accept=".bin"><br><button id="go">Оновити прошивку</button><p id="status"></p><a href="/">Повернутися до панелі</a>
<script>const b=document.getElementById('go'),s=document.getElementById('status');b.onclick=async()=>{const f=document.getElementById('file').files[0];if(!f){s.textContent='Виберіть firmware.bin';return;}b.disabled=true;const data=new FormData();data.append('firmware',f);const x=new XMLHttpRequest();x.open('POST','/update');x.setRequestHeader('X-R1-Panel','1');x.setRequestHeader('X-R1-Size',String(f.size));x.upload.onprogress=e=>{s.textContent=e.lengthComputable?'Передано '+Math.round(e.loaded/e.total*100)+'% — очікуємо перевірки':'Передавання…';};x.onload=()=>{s.textContent=x.responseText;b.disabled=false;if(x.status===200)setTimeout(()=>location.href='/',6000);};x.onerror=()=>{s.textContent='Зв’язок перервано. Перевірте стан R1 перед повторенням.';b.disabled=false;};x.send(data);};</script></html>)HTML";
}
bool otaOwnerPoll(){
    static bool held=false;
    if(maintenance.load()==1){
        if(recorder::busy()||ecosystemLinkedActive()||!sd_files::lockForUpdate())maintenance.store(3);
        else {acquisitionPause();held=true;int request=1;if(!maintenance.compare_exchange_strong(request,2)){sd_files::unlockForUpdate();acquisitionResume();held=false;}}
    }
    if(held&&maintenance.load()!=2){sd_files::unlockForUpdate();acquisitionResume();held=false;}
    if(held){delay(1);return true;}
    return false;
}
void otaRoutes(WebServer& server,const char* password){
    server.on("/api/ota",HTTP_GET,[&server,password]{
        if(!server.authenticate("admin",password)){server.requestAuthentication();return;}
        const auto* running=esp_ota_get_running_partition();const auto* next=esp_ota_get_next_update_partition(nullptr);
        server.sendHeader("Cache-Control","no-store");
        server.send(200,"application/json",String("{\"slot\":\"")+(running?running->label:"")+"\",\"max_bytes\":"+String(next?next->size:0)+"}");
    });
    server.on("/update",HTTP_GET,[&server,password]{
        if(!server.authenticate("admin",password)){server.requestAuthentication();return;}
        server.sendHeader("Cache-Control","no-store");server.send(200,"text/html; charset=utf-8",PAGE);
    });
    server.on("/update",HTTP_POST,[&server,password]{
        if(!server.authenticate("admin",password)){server.requestAuthentication();return;}
        bool ok=complete&&!writing&&rebootAt==0;
        if(ok&&!Update.end(false)){abortUpload("Invalid firmware image");ok=false;}
        server.send(ok?200:400,"text/plain; charset=utf-8",ok?"Прошивку перевірено. R1 перезапускається.":failure.length()?failure:"No complete firmware upload");
        if(ok)rebootAt=millis()+1500;
    },[&server,password]{
        HTTPUpload& u=server.upload();
        if(u.status==UPLOAD_FILE_START){
            if(rebootAt)return;
            // A second file in one multipart request must never activate another image.
            if(complete){abortUpload("Only one firmware file allowed");return;}
            failure="";expected=received=0;
            if(!server.authenticate("admin",password)){failure="Authentication required";return;}
            if(server.header("X-R1-Panel")!="1" || (server.hasHeader("Origin")&&server.header("Origin")!=String("http://")+server.hostHeader())){failure="Origin/header rejected";return;}
            const String size=server.header("X-R1-Size");
            if(size.length()==0||size.length()>8){failure="Invalid image size";return;}
            for(char c:size){if(c<'0'||c>'9'){failure="Invalid image size";return;}expected=expected*10+c-'0';}
            const esp_partition_t* target=esp_ota_get_next_update_partition(nullptr);
            if(!target||expected<288||expected>target->size){failure="Image does not fit OTA slot";return;}
            if(!reserve()){failure="Stop recording and close SD transfers before OTA";return;}
            // Defer Update.begin until the first header has been validated.
            writing=true;touched=millis();
        }else if(u.status==UPLOAD_FILE_WRITE && writing){
            touched=millis();
            if(received==0){
                if(u.currentSize<24||u.buf[0]!=0xe9||u.buf[12]!=9||u.buf[13]!=0){abortUpload("Not an ESP32-S3 application image");return;}
                if(!Update.begin(expected,U_FLASH)){abortUpload("Cannot open OTA slot");return;}
            }
            if(u.currentSize>expected-received || Update.write(u.buf,u.currentSize)!=u.currentSize){abortUpload("OTA write failed or oversized image");return;}
            received+=u.currentSize;
        }else if(u.status==UPLOAD_FILE_END && writing){
            if(received!=expected){abortUpload("Incomplete firmware");return;}
            writing=false;complete=true;touched=millis();
        }else if(u.status==UPLOAD_FILE_ABORTED){abortUpload("Upload interrupted; current firmware retained");}
    });
}
void otaTick(){
    if(rebootAt&&int32_t(millis()-rebootAt)>=0)ESP.restart();
    if((writing||complete)&&!rebootAt&&millis()-touched>15000)abortUpload("Upload timed out");
}
