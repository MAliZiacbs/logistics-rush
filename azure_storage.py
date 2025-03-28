# azure_storage.py
import streamlit as st
from azure.storage.blob import BlobServiceClient, ContentSettings

def get_blob_service_client():
    """Get blob service client using storage account key"""
    try:
        # Get credentials from Streamlit secrets
        account_name = st.secrets["azure"]["storage_account"]
        account_key = st.secrets["azure"]["storage_account_key"]
        
        # Create connection string
        conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        
        # Create the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        
        return blob_service_client
    
    except Exception as e:
        print(f"Error connecting to Azure: {e}")
        return None