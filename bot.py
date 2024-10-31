import os
import telebot
import yt_dlp
from youtubesearchpython import VideosSearch
from googleapiclient.discovery import build
import json
import re
import speech_recognition as sr
BOT_TOKEN = os.environ.get("BOTTKN")
bot = telebot.TeleBot(BOT_TOKEN)
YOUTUBE_API_KEY = os.environ.get("YTK")
recognizer = sr.Recognizer()

def search_youtube(query):
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    if result['result']:
        video = result['result'][0]
        video_id = video['id']
        video_link = f"https://www.youtube.com/watch?v={video_id}"
        return {'id': video_id, 'link': video_link}
    return None

def format_duration(duration):
    # Regex to parse the ISO 8601 duration format
    match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', duration)
    minutes = match.group(1) if match.group(1) else '0'
    seconds = match.group(2) if match.group(2) else '0'
    return f"{minutes} min {seconds} sec"

def shorten_description(description, max_length=300):
    # Shorten description to a specified max length
    if len(description) <= max_length:
        return description
    return description[:max_length] + '...'

def get_video_details(video_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.videos().list(
        part='snippet,contentDetails',
        id=video_id
    )
    response = request.execute()

    print(json.dumps(response, indent=2))  # Print the response for debugging

    if response['items']:
        video = response['items'][0]
        snippet = video['snippet']
        content_details = video['contentDetails']
        
        description = snippet.get('description', '')
        shortened_description = shorten_description(description)
        
        details = {
            'title': snippet.get('title', 'Unknown Title'),
            'artist': snippet.get('channelTitle', 'Unknown Artist'),
            'description': shortened_description,
            'publishedAt': snippet.get('publishedAt', 'Unknown Date'),
            'duration': format_duration(content_details.get('duration', 'PT0M0S'))
        }
        return details
    return {}

def get_song_details(song):
    video_info = search_youtube(song)
    if video_info:
        details = get_video_details(video_info['id'])
        response = (
            f"🎵 *Title:* {details['title']}\n\n"
            f"🎤 *Artist:* {details['artist']}\n\n"
            f"📝 *Description:* {details['description']}\n\n"
            f"📅 *Published At:* {details['publishedAt']}\n\n"
            f"⏳ *Duration:* {details['duration']}"
        )
        return response
    else:
        return "Song not found"

def download_music(url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': output_path,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_song(song_name):
    video_info = search_youtube(song_name)
    if video_info:
        url = video_info['link']
        output_path = f"{song_name}.mp3"
        download_music(url, output_path)
        print(f"Downloaded: {output_path}")
        return output_path
    else:
        print("Song not found")
        return None

@bot.message_handler(commands=['start', 'hello', 'hi'])
def send_welcome(message):
    bot.reply_to(message, "Hi! I'm Shazam bot. 👋\nNice to meet you. 😊\nGive me a title track or song lyrics and I'll download the song for you!")

@bot.message_handler(commands=['recognize'])
def recognize_song(message):
    with sr.Microphone() as source:
        bot.send_message(message.chat.id, "Listening...")
        audio = recognizer.listen(source)
    
    try:
        song_name = recognizer.recognize_google(audio)
        bot.send_message(message.chat.id, f"🎧 Recognized song: {song_name}")
        bot.send_message(message.chat.id, "Searching on web...")
        song_details = get_song_details(song_name)
        bot.send_message(message.chat.id, song_details)
        download_song(song_name)
        bot.send_message(message.chat.id, "Your requested song is ready! 🎶\nPlease provide the name of the song with the /send_audio command.")
    except sr.UnknownValueError:
        bot.send_message(message.chat.id, "Sorry, I did not understand that.")
    except sr.RequestError:
        bot.send_message(message.chat.id, "Sorry, there was an issue with the API due to server problem. Please try again later!")

@bot.message_handler(commands=['send_audio'])
def send_audio(message):
    parts = message.text.split(maxsplit=1)
    song_name = parts[1] if len(parts) > 1 else None
    if song_name:
        audio_path = f"{song_name}.mp3"
        if os.path.exists(audio_path):
            with open(audio_path, 'rb') as audio:
                try:
                    bot.send_audio(message.chat.id, audio, timeout=120)
                    bot.reply_to(message, "Your audio is successfully downloaded!\nEnjoy 😊🥂")
                except Exception as e:
                    bot.reply_to(message, f"Failed to send audio: {e}\nTry again with the command /send_audio")
                finally:
                    os.remove(audio_path)
        else:
            bot.reply_to(message, "Sorry, I couldn't find the audio file. Please try again.")
    else:
        bot.reply_to(message, "Please provide the name of the song with the /send_audio command.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "Processing...Please wait a moment!")
    song_name = message.text
    audio_file = download_song(song_name)
    
    if audio_file and os.path.exists(audio_file):
        bot.reply_to(message, "Your requested song is ready! 🎶\nPlease provide the name of the song with the /send_audio command.")
    else:
        bot.reply_to(message, "Sorry, I couldn't find or download the song.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "Nice photo! I'll process it. It's better to give me the name of a title track.")

bot.infinity_polling()
