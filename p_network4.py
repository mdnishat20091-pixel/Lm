from p_base import BaseProvider


class Network4Provider(BaseProvider):
    """2EEE7 NETWORK: ডকুমেন্টেশন অসম্পূর্ণ, তাই যাচাই না হওয়া পর্যন্ত নিষ্ক্রিয়।
    কোনো এন্ডপয়েন্ট, হেডার বা ফরম্যাট অনুমান করা হয়নি।"""

    slug = "network4"
    name = "2EEE7 NETWORK"
    default_base_url = None
    auth_header = "—"
    verified = False
