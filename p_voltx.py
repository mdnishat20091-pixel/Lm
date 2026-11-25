from p_base import BaseProvider


class VoltxProvider(BaseProvider):
    slug = "voltx"
    name = "VOLTX SMS"
    default_base_url = "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
    auth_header = "mauthapi"
    test_method = "GET"
    test_path = "/liveaccess"  # প্ল্যানে তালিকাভুক্ত এন্ডপয়েন্ট
    verified = True
