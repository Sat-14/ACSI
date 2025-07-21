# test_api.py - Script to test the Flask API endpoints

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def test_process_channel(channel_handle):
    """Test the process_channel endpoint"""
    print(f"\nTesting channel processing for: {channel_handle}")
    
    response = requests.post(
        f"{BASE_URL}/process_channel",
        json={"channel_handle": channel_handle}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Processed {len(data['results']['processed_videos'])} videos")
        for video in data['results']['processed_videos']:
            print(f"  - {video['title']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

def test_process_video(video_url):
    """Test the process_video endpoint"""
    print(f"\nTesting video processing for: {video_url}")
    
    response = requests.post(
        f"{BASE_URL}/process_video",
        json={"video_url": video_url}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Transcript saved to: {data['transcript_path']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

def test_list_transcripts():
    """Test the list_transcripts endpoint"""
    print("\nListing all transcripts...")
    
    response = requests.get(f"{BASE_URL}/transcripts")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['transcripts'])} transcripts:")
        for transcript in data['transcripts'][:5]:  # Show first 5
            print(f"  - {transcript['filename']} ({transcript['size']} bytes)")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

def test_get_transcript(filename):
    """Test the get_transcript endpoint"""
    print(f"\nGetting transcript: {filename}")
    
    # Test JSON format
    response = requests.get(f"{BASE_URL}/transcript/{filename}?format=json")
    
    if response.status_code == 200:
        data = response.json()
        content = data['content']
        print(f"Success! Content preview (first 200 chars):")
        print(content[:200] + "...")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_api.py channel @channelname")
        print("  python test_api.py video https://youtube.com/watch?v=...")
        print("  python test_api.py list")
        print("  python test_api.py get filename.txt")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "channel" and len(sys.argv) >= 3:
        test_process_channel(sys.argv[2])
    elif command == "video" and len(sys.argv) >= 3:
        test_process_video(sys.argv[2])
    elif command == "list":
        test_list_transcripts()
    elif command == "get" and len(sys.argv) >= 3:
        test_get_transcript(sys.argv[2])
    else:
        print("Invalid command or missing arguments")

if __name__ == "__main__":
    main()