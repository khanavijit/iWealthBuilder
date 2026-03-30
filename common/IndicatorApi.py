import time
from datetime import datetime
import streamlit as st
import boto3
import requests
from requests import Timeout

from Constants import INDICATOR_API_IP


class IndicatorApi:
    def __init__(self, username, password, host=None):
        self.username = username
        self.password = password
        self.base_url, self.host_ip = get_indicator_api_host(host)
        self.token = None
        self.__service_config = {
            # 'host': host,
            'routes': {
                'login': '/login',
                'get_stock_data': '/get_stock_data',
                'get_global_indicator_data': '/get_global_indicator_data',
                'get_index_data': '/get_index_data',
                'health': '/health'
            }
        }

    def login(self):
        login_url = self.base_url + self.__service_config['routes']['login']
        data = {
            'username': self.username,
            'password': self.password
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(login_url, json=data, headers=headers, timeout=1)

            if response.status_code == 200:
                if token := response.json().get('access_token'):
                    self.token = token
                    # print("Login successful")
                    return True
                else:
                    print("Token not received")
            else:
                print(f"Login failed with status code: {response.status_code}")

        except Timeout:
            print("Request timed out for Login. Please try again.")

        return False

    def get_index_data(self):
        if self.token is None:
            print("Please login first.")
            return None

        index_data_url = self.base_url + self.__service_config['routes']['get_index_data']
        headers = {
            'Authorization': f'Bearer {self.token}'
        }

        response = requests.get(index_data_url, headers=headers)

        if response.status_code == 200:
            return response.json()
        print("Failed to invoke the custom API")
        return None

    def check_indicator_health(self):
        health_url = self.base_url + self.__service_config['routes']['health']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

        try:
            response = requests.get(health_url, headers=headers, timeout=1)

            if response.status_code == 200:
                print(f"Rest API health {response.json()}")
                return True
            else:
                print(f"Rest API is not up : {response.status_code}")
                return False
        except Timeout:
            print("Request timed out. Please try again.")
        return False

    def get_stock_data(self, stock_symbol, days_ago=730, index_flag=False):
        if self.token is None:
            print("Please login first.")
            return None

        stock_data_url = self.base_url + self.__service_config['routes']['get_stock_data']
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        if index_flag:
            params = {
                'stock_symbol': stock_symbol,
                'days_ago': days_ago,
                'index_flag': True,
            }
        else:
            params = {
                'stock_symbol': stock_symbol,
                'days_ago': days_ago
            }

        response = requests.get(stock_data_url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        print("Failed to invoke the custom API")
        return None

    # @st.cache_data(ttl=3600)
    def get_global_indicator_data(_self, symbol, years_ago=15, apply_indicator=True, length=34, multiplier=4.5, ao_threshold=200):
        if _self.token is None:
            print("Please login first.")
            return None

        stock_data_url = _self.base_url + _self.__service_config['routes']['get_global_indicator_data']
        headers = {
            'Authorization': f'Bearer {_self.token}'
        }
        if apply_indicator:
            params = {
                'symbol': symbol,
                'years_ago': years_ago,
                'length': length,
                'multiplier': multiplier,
                'ao_threshold': ao_threshold,
                'apply_indicator': apply_indicator
            }
        else:
            params = {
                'symbol': symbol,
                'years_ago': years_ago,
                'apply_indicator': apply_indicator
            }

        print(params)
        response = requests.get(stock_data_url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        print("Failed to invoke the custom API")
        return None


def get_indicator_api_host(host_ip=None):
    if host_ip is None:
        host_ip = get_parameter_from_aws(parameter_name=INDICATOR_API_IP)
    return f'http://{host_ip}:8080', host_ip

def get_parameter_from_aws(parameter_name='SHOONYA_AUTH_TOKEN'):
    flag = False
    parameter_value = None
    start_time = datetime.now()
    while ((datetime.now() - start_time).total_seconds() < 120) and not flag:
        try:
            ssm = boto3.client('ssm', region_name='ap-south-1')
            parameter_value = ssm.get_parameter(Name=parameter_name, WithDecryption=True)['Parameter']['Value']
            if parameter_value == 'Invalid':
                parameter_value = None
            flag = True
        except Exception as e:
            print(f"Error  {e} ")
        if not flag:
            time.sleep(1)

    return parameter_value


