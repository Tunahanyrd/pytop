# processes.py
import psutil
import threading
import time
from typing import List, Dict, Any

class ProcessManager:
    def __init__(self,
                 interval:float=1.0,
                 attrs: List[str]=None,
                 ad_value: Any=None):
        """
        interval: update period (sec)
        attrs: psutil.process_iter attribute
        ad_value: Value to be used in case of AccessDenied/ZombieProcess
        """
        self.interval = interval
        self.attrs = attrs or ['pid', 'name', 'username', 'cpu_percent', 'memory_percent']
        self.ad_value = ad_value
        
        self._processes:List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = threading.Thread(target=self._update_loop, 
                                        daemon=True)
    
    def start(self):
        """Update process list in background"""
        if self._running:
            return
        self._running = True
        
        """cold start"""
        for _ in range(2):
            for _ in psutil.process_iter(attrs=self.attrs,
                                         ad_value=self.ad_value):
                pass
            
        time.sleep(1)
        self._thread.start()  
    def stop(self):
        "stop update and make join"
        if not self._running:
            return
        self._running = False
        self._thread.join()
    
    def _update_loop(self):
        "always working update loop"
        while self._running:
            snapshot: List[Dict[str, Any]] = []
            for proc in psutil.process_iter(attrs=self.attrs, ad_value=self.ad_value):
                snapshot.append(proc.info)
            
            with self._lock:
                del self._processes[:]
                self._processes.extend(snapshot)
            
            time.sleep(self.interval)
    
    def get_processes(self) -> List[Dict[str, Any]]:
        """
        Instant process list.
        changing the returned list does not affect the main list.
        """
        with self._lock:
            return list(self._processes) # return its copy
    
    def sort_processes(self, 
                       by:str="cpu_percent", 
                       reverse:bool=True) -> List[Dict[str, Any]]:
        procs = self.get_processes()
        return sorted(procs, key=lambda p: p.get(by, 0), reverse=reverse)
    
    def filter_by_user(self, uname:str) -> List[Dict[str, any]]:
        return [p for p in self.get_processes() if p.get("username") == uname]