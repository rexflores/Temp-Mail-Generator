#!/usr/bin/env python3
"""
Test URL conversion functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import convert_urls_to_links

def test_url_conversion():
    """Test URL conversion function"""
    
    print("Testing URL Conversion...")
    print("=" * 50)
    
    # Test case similar to your email
    test_email = """[https://pointblank.zepetto.com/images/common/email/logo_gnb_pb_new_verkr48.png]
[https://u9330588.ct.sendgrid.net/ls/click?upn=u001.HMg-2Bh3ZCu3lRvXShYNod1IS8JrPgi7gNoT83qieJLmsULaKAqht0CJxYvyQlSbWlIuy1_cSk1xFCZ-2BjyIQRb88Er7S2bcWHu5kvh7mLcFDrJPYE4L-2BJLeOFkujPsgNa9PQr1IGNrPfHM6rkTWoP8UkuipErSvf-2Bqi7-2F-2FMwDvX7Ha74puuGQ6Izl6br21SPYt8qzfMuKdElgCFkDLpG4i9QiYq4IZvUmjdBgX19cd6yYEABWoccY-2Fr-2BI3ra7LIMOtE6nNS6xsO4OFdgfQhmbeKP26gRg-3D-3D]
       

Hello! Enter the OTP within the specified time. OTP : 829165

               

This e-mail is no-reply e-mail. Please email us at cs@zepetto.co.th
[cs@zepetto.co.th]
Copyright Zepetto (Thailand) co.,l.td. All rights reserved.
[https://pointblank.zepetto.com/images/common/email/logo_zepetto_b.png]"""

    print("Original email content:")
    print("-" * 30)
    print(test_email)
    print("\n")
    
    print("Converted email content:")
    print("-" * 30)
    converted = convert_urls_to_links(test_email)
    print(converted)
    print("\n")
    
    print("HTML tags found:")
    print("-" * 30)
    import re
    links = re.findall(r'<a[^>]*>(.*?)</a>', converted)
    print(f"Number of links created: {len(links)}")
    for i, link in enumerate(links, 1):
        print(f"  {i}. {link}")

if __name__ == "__main__":
    test_url_conversion()