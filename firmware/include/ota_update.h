#pragma once
class WebServer;
void otaRoutes(WebServer& server, const char* password);
void otaTick();
// Called only by the hardware owner, before handling commands/acquisition.
bool otaOwnerPoll();
