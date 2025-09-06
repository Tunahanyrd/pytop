import psutil

class WinServices:
    def list_services(self):
        return list(psutil.win_service_iter())

    def get_service(self, name: str):
        return psutil.win_service_get(name)
