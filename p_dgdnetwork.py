from p_base import BaseProvider


class DgdNetworkProvider(BaseProvider):
    slug = "dgdnetwork"
    name = "DGDNETWORK"
    default_base_url = "https://dgddigital.com"
    auth_header = "X-API-KEY"
    extra_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    test_method = "GET"
    test_path = "/api/v1/user/checknum"  # প্ল্যানে তালিকাভুক্ত এন্ডপয়েন্ট
    verified = True
    rate_limit_per_min = 25  # ডকুমেন্টেড ডিফল্ট সীমা
