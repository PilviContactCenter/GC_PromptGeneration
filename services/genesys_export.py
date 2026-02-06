import PureCloudPlatformClientV2
from PureCloudPlatformClientV2.rest import ApiException
import os
from config import Config
import requests

def get_api_client_and_token():
    """Returns tuple of (api_client, access_token)"""
    
    if not Config.GENESYS_CLIENT_ID or not Config.GENESYS_CLIENT_SECRET:
        raise ValueError("Genesys Cloud credentials are not configured.")

    region_mapping = {
        'mypurecloud.com': 'us_east_1',
        'us_east_1': 'us_east_1',
        'mypurecloud.de': 'eu_central_1',
        'eu_central_1': 'eu_central_1',
        'mypurecloud.ie': 'eu_west_1',
        'eu_west_1': 'eu_west_1',
        'mypurecloud.com.au': 'ap_southeast_2',
        'ap_southeast_2': 'ap_southeast_2',
        'mypurecloud.jp': 'ap_northeast_1',
        'ap_northeast_1': 'ap_northeast_1',
    }

    region_key = region_mapping.get(Config.GENESYS_REGION, Config.GENESYS_REGION)

    try:
        region = getattr(PureCloudPlatformClientV2.PureCloudRegionHosts, region_key)
    except AttributeError:
        if hasattr(PureCloudPlatformClientV2.PureCloudRegionHosts, Config.GENESYS_REGION):
            region = getattr(PureCloudPlatformClientV2.PureCloudRegionHosts, Config.GENESYS_REGION)
        else:
            raise ValueError(f"Invalid Genesys Region: {Config.GENESYS_REGION}")

    PureCloudPlatformClientV2.configuration.host = region.get_api_host()

    api_client = PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
        Config.GENESYS_CLIENT_ID,
        Config.GENESYS_CLIENT_SECRET
    )
    
    # Get access token directly from api_client
    access_token = api_client.access_token
    print(f"Token retrieved: {access_token[:30] if access_token else 'None'}...")
    
    return api_client, access_token

def list_prompts(page_number=1, page_size=25, name_filter=None, sort_by="name", sort_order="asc"):
    """
    Lists all prompts from Genesys Cloud Architect.
    
    Args:
        page_number: Page number for pagination (1-indexed)
        page_size: Number of prompts per page (max 100)
        name_filter: Optional filter by prompt name (partial match)
        sort_by: Field to sort by (name, description)
        sort_order: Sort order (asc, desc)
    
    Returns:
        dict with 'prompts' list and 'pagination' info
    """
    api_client, _ = get_api_client_and_token()
    architect_api = PureCloudPlatformClientV2.ArchitectApi(api_client)
    
    try:
        # Get prompts with optional filtering
        kwargs = {
            'page_number': page_number,
            'page_size': min(page_size, 100),
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        
        if name_filter:
            kwargs['name'] = f"*{name_filter}*"
        
        result = architect_api.get_architect_prompts(**kwargs)
        
        prompts = []
        if result.entities:
            for prompt in result.entities:
                # Safely get date attributes (may not exist in all SDK versions)
                created = getattr(prompt, 'date_created', None)
                modified = getattr(prompt, 'date_modified', None)
                prompts.append({
                    'id': prompt.id,
                    'name': prompt.name,
                    'description': prompt.description or '',
                    'created_date': created.isoformat() if created else None,
                    'modified_date': modified.isoformat() if modified else None
                })
        
        return {
            'prompts': prompts,
            'pagination': {
                'page_number': result.page_number,
                'page_size': result.page_size,
                'page_count': result.page_count,
                'total': result.total
            }
        }
    
    except ApiException as e:
        print(f"Error listing prompts: {e}")
        raise Exception(f"Failed to list prompts: {e.status} - {e.reason}")


def get_prompt_resources(prompt_id):
    """
    Gets all language resources for a prompt, including audio media URIs.
    
    Args:
        prompt_id: The Genesys Cloud prompt ID
    
    Returns:
        list of resource objects with language and media_uri
    """
    api_client, access_token = get_api_client_and_token()
    architect_api = PureCloudPlatformClientV2.ArchitectApi(api_client)
    
    try:
        # Get prompt resources
        result = architect_api.get_architect_prompt_resources(prompt_id)
        
        resources = []
        if result.entities:
            for resource in result.entities:
                resource_data = {
                    'id': resource.id,
                    'language': resource.language,
                    'media_uri': resource.media_uri or None,
                    'upload_status': resource.upload_status or 'unknown',
                    'has_audio': bool(resource.media_uri),
                    'duration_seconds': resource.duration_seconds if hasattr(resource, 'duration_seconds') else None
                }
                resources.append(resource_data)
        
        return resources
    
    except ApiException as e:
        print(f"Error getting prompt resources: {e}")
        raise Exception(f"Failed to get prompt resources: {e.status} - {e.reason}")


def get_prompt_audio_url(prompt_id, language):
    """
    Gets the audio URL for a specific prompt and language.
    
    Args:
        prompt_id: The Genesys Cloud prompt ID
        language: Language code (e.g., 'en-us')
    
    Returns:
        Audio URL string or None if not found
    """
    api_client, access_token = get_api_client_and_token()
    architect_api = PureCloudPlatformClientV2.ArchitectApi(api_client)
    
    try:
        resource = architect_api.get_architect_prompt_resource(prompt_id, language)
        
        if resource and resource.media_uri:
            return resource.media_uri
        
        return None
    
    except ApiException as e:
        if e.status == 404:
            return None
        print(f"Error getting prompt audio: {e}")
        raise Exception(f"Failed to get prompt audio: {e.status} - {e.reason}")


def upload_prompt_to_genesys(file_path, prompt_name, description="Generated by PromptApp", language="en-us"):
    """
    Uploads a WAV file to Genesys Cloud Architect Prompts.
    
    Args:
        file_path: Path to the WAV file
        prompt_name: Name for the prompt in Genesys Cloud
        description: Optional description
        language: Language code (e.g., 'en-us', 'de-de', 'fr-fr')
    """
    api_client, access_token = get_api_client_and_token()
    architect_api = PureCloudPlatformClientV2.ArchitectApi(api_client)

    # 1. Create prompt or find existing
    body = PureCloudPlatformClientV2.Prompt()
    body.name = prompt_name
    body.description = description
    
    prompt_id = None
    try:
        print(f"Creating prompt '{prompt_name}'...")
        prompt = architect_api.post_architect_prompts(body)
        prompt_id = prompt.id
        print(f"Prompt created with ID: {prompt_id}")
    except ApiException as e:
        if e.status == 409:  # Conflict - already exists
            print(f"Prompt already exists, searching...")
            existing = architect_api.get_architect_prompts(name=prompt_name)
            if existing and existing.entities:
                prompt = existing.entities[0]
                prompt_id = prompt.id
                print(f"Found existing prompt ID: {prompt_id}")
            else:
                raise Exception(f"Prompt exists but couldn't find it: {e}")
        else:
            raise e

    if not prompt_id:
        raise Exception("Failed to create or find prompt")

    # 2. Create prompt resource for the specified language
    print(f"Using language: {language}")
    
    try:
        # Check if resource already exists and delete it
        try:
            existing_resource = architect_api.get_architect_prompt_resource(prompt_id, language)
            if existing_resource:
                print(f"Resource exists, deleting to recreate...")
                architect_api.delete_architect_prompt_resource(prompt_id, language)
                print("Deleted existing resource.")
        except ApiException as check_e:
            if check_e.status != 404:
                print(f"Warning checking existing resource: {check_e.status}")
        
        # Create new resource
        resource_body = PureCloudPlatformClientV2.PromptAsset()
        resource_body.language = language
        
        print(f"Creating resource for language {language}...")
        result_resource = architect_api.post_architect_prompt_resources(prompt_id, resource_body)
        upload_uri = result_resource.upload_uri
        
        if not upload_uri:
            raise Exception("No upload URI returned from Genesys")
        
        print(f"Upload URI: {upload_uri}")
        print(f"Uploading file via multipart POST...")
        
        # Multipart POST with file as form-data
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'audio/wav')
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            upload_response = requests.post(
                upload_uri, 
                files=files,
                headers=headers
            )
        
        print(f"Upload response status: {upload_response.status_code}")
        
        if upload_response.status_code in [200, 201, 202, 204]:
            print("Upload completed successfully!")
            return True
        else:
            print(f"Upload response body: {upload_response.text[:500] if upload_response.text else 'empty'}")
            raise Exception(f"Upload failed with status {upload_response.status_code}: {upload_response.text}")
            
    except ApiException as e:
        print(f"Error handling prompt resources: {e}")
        raise Exception(f"Genesys API Error: {e.status} - {e.reason}")

    return False
