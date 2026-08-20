import pandas as pd

FEATURES = [
    # CPU/load
    "cpu_r",
    "load_1",
    "load_5",
    "load_15",

    # Memory pressure
    "mem_u",
    "mem_u_e",
    "si",
    "so",

    # Disk
    "disk_q",
    "disk_r",
    "disk_rb",
    "disk_svc",
    "disk_u",
    "disk_w",
    "disk_wa",
    "disk_wb",

    # Network traffic
    "eth1_fi",
    "eth1_fo",
    "eth1_pi",
    "eth1_po",

    # TCP health
    "tcp_tw",
    "tcp_use",
    "curr_estab",
    "active_opens",
    "passive_opens",
    "in_errs",
    "listen_overflows",
    "out_rsts",
    "retransegs",
    "tcp_timeouts",

    # UDP errors
    "udp_rcv_buf_errs",
    "udp_snd_buf_errs",
]



METADATA = ["timestamp"]


class Dataset():

    def __init__(self, data):
        self.data = pd.DataFrame(data=data)
        self.metadata = self.data[METADATA]
        
    def _preprocess_dataset(data):
        return data[FEATURES]

    def transform_oltp_data():
        pass
        