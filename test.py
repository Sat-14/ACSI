#!/usr/bin/env python3
"""
Test script to process a single video for debugging
"""

import os
import sys

# Ensure we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_processor import VideoProcessor
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_video(video_url):
    """Test processing a single video"""
    print(f"\nTesting video processing for: {video_url}")
    print("=" * 60)
    
    try:
        # Initialize processor
        print("Initializing video processor...")
        processor = VideoProcessor()
        print("✓ Processor initialized")
        
        # Process video
        print("\nProcessing video...")
        result = processor.process_single_video(video_url)
        
        # Show results
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        
        if result['success']:
            print(f"✓ SUCCESS!")
            print(f"  - Video: {result['video_info']['title']}")
            print(f"  - Summary saved to: {result['transcript_path']}")
            print(f"  - Topic: {result['topic']}")
            print(f"  - Summary preview: {result['summary'][:100]}...")
        else:
            print(f"✗ FAILED!")
            print(f"  - Error: {result['error']}")
            
    except Exception as e:
        print(f"\n✗ EXCEPTION: {e}")
        print(f"  - Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

def test_channel(channel_name):
    """Test processing a channel"""
    print(f"\nTesting channel processing for: {channel_name}")
    print("=" * 60)
    
    try:
        # Initialize processor
        print("Initializing video processor...")
        processor = VideoProcessor()
        print("✓ Processor initialized")
        
        # Process channel
        print("\nProcessing channel...")
        result = processor.process_channel(channel_name)
        
        # Show results
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        
        print(f"Channel: {result['channel']}")
        print(f"Videos processed: {len(result['processed_videos'])}")
        print(f"Errors: {len(result['errors'])}")
        
        if result['processed_videos']:
            print("\nProcessed videos:")
            for video in result['processed_videos']:
                print(f"  ✓ {video['title']}")
                
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  ✗ {error}")
                
    except Exception as e:
        print(f"\n✗ EXCEPTION: {e}")
        print(f"  - Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check API key
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not set!")
        print("Please set your API key in config.py or as an environment variable")
        sys.exit(1)
    
    print("YouTube Video Processor Test")
    print("=" * 60)
    
    # Test options
    print("\nWhat would you like to test?")
    print("1. Process a single video")
    print("2. Process a channel")
    print("3. Test with a short video")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        url = input("Enter video URL: ").strip()
        if url:
            test_single_video(url)
    elif choice == '2':
        channel = input("Enter channel name (e.g., @MrBeast): ").strip()
        if channel:
            test_channel(channel)
    elif choice == '3':
        # Test with a known short video
        print("\nTesting with a short video...")
        test_single_video("https://www.youtube.com/watch?v=jNQXAC9IVRw")  # "Me at the zoo" - first YouTube video, 19 seconds
    else:
        print("Invalid choice")
        
    print("\nTest complete!")
