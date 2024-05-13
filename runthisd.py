import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import json
import requests
import logging
from win11toast import toast
import pyperclip
logging.basicConfig( filename= "./ntfywinservice.log",encoding="utf8",level= logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import multiprocessing
class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "NtfyStreamingReciverService"
    _svc_display_name_ = "NtfyStreamingReciverService"

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None,0,0,"NtfyStreamingReciverServiceEvent")
        socket.setdefaulttimeout(60)
        self.stop = True

    def SvcStop(self):
        self.stop = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        # self.stop = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,'service started'))
        self.main()
    def loadconfig(self):
        try:
            config = json.load(open("config.json"))
            #load header
            header = {
                "Authorization": config["Authorization"]
            }
            #load url
            url = config["url"]
            if not url:
                url = "https://ntfy.sh"
            if "/" != url[-1]:
                url = url+"/"
            #load topic
            topic = config["topic"]
            if not topic:
                raise ValueError
            #load Priority
            priority = config["Priority"]
            if not priority:
                priority = "all"
            #load Tags
            tags = config["Tags"]
            if not tags:
                tags = "all"
            return header,url,topic
        except Exception as e:
            servicemanager.LogErrorMsg("Could not load config.json")
            logging.error(e)
    def main(self):
        header,url,topic = self.loadconfig()
        logging.info("loaded the config")
        streaming = requests.get(f"{url}{topic}/json", stream=True,headers=header)
        logging.info("started the streaming....")
        # def toastrec(message):
            # return toast(message)
        while self.stop:
            try:
                for line in streaming.iter_lines():
                    if not self.stop:
                        break
                    if line:
                        content = json.loads(line)
                        logging.info(str(content))
                        if content["event"]=="message" and content["topic"]==topic and topic in content["message"]:
                            messagejson = json.loads(content["message"])
                            logging.info(messagejson[topic])
                            try:
                                message = messagejson[topic]
                                # th = threading.Thread(target=toastrec,args=((messagejson[topic],lambda a:pyperclip.copy(messagejson[topic])))).start()
                                t = multiprocessing.Process(target=toast,args=(message,))
                                t.start()
                                t.join()
                                # t.run()
                                # t.join()
                                # toast(messagejson[topic])
                            except Exception as e:
                                logging.error("toast message failed.")
                                logging.error(e)
                            # logging.info(messagejson[topic])
            except Exception as e:
                logging.error(e)
                servicemanager.LogErrorMsg("Streaming failed,retrying...")
        else:
            logging.info("stopped the service....")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)