from p_base import BaseProvider


class MkNetworkProvider(BaseProvider):
    slug = "mknetwork"
    name = "MK NETWORK"
    default_base_url = "https://mknetworkbd.com/api/v3/public"
    auth_header = "mknetwork-key"
    test_method = "GET"
    test_path = "/whoami"  # প্ল্যানে তালিকাভুক্ত এন্ডপয়েন্ট
    verified = True
