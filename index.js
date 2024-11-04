const { exec } = require('child_process');
const { Telegraf } = require('telegraf');
const fs = require('fs');
const { YouTube_API_KEY, Shazam_Bot } = process.env;
const axios = require('axios');

const bot = new Telegraf(Shazam_Bot);
const lastSongRequested = {};  // To store last requested song for each user

async function searchYouTube(query) {
    try {
        const response = await axios.get(`https://www.googleapis.com/youtube/v3/search`, {
            params: {
                part: 'snippet',
                q: query,
                key: YouTube_API_KEY,
                maxResults: 1,
                type: 'video'
            }
        });
        
        const video = response.data.items[0];
        if (video) {
            return {
                id: video.id.videoId,
                link: `https://www.youtube.com/watch?v=${video.id.videoId}`
            };
        }
    } catch (error) {
        console.error('Error searching YouTube:', error);
    }
    return null;
}

function formatDuration(duration) {
    const match = duration.match(/PT(?:(\d+)M)?(?:(\d+)S)?/);
    const minutes = match[1] || '0';
    const seconds = match[2] || '0';
    return `${minutes} min ${seconds} sec`;
}

async function getVideoDetails(videoId) {
    try {
        const response = await axios.get(`https://www.googleapis.com/youtube/v3/videos`, {
            params: {
                part: 'snippet,contentDetails',
                id: videoId,
                key: YouTube_API_KEY
            }
        });

        const video = response.data.items[0];
        if (video) {
            return {
                title: video.snippet.title,
                artist: video.snippet.channelTitle,
                description: video.snippet.description,  // Send full description without slicing
                publishedAt: video.snippet.publishedAt,
                duration: formatDuration(video.contentDetails.duration)
            };
        }
    } catch (error) {
        console.error('Error getting video details:', error);
    }
    return {};
}

async function getSongDetails(song) {
    const videoInfo = await searchYouTube(song);
    if (videoInfo) {
        const details = await getVideoDetails(videoInfo.id);
        return `🎵 *Title:* ${details.title}\n\n🎤 *Artist:* ${details.artist}\n\n📝 *Description:* ${details.description}\n\n📅 *Published At:* ${details.publishedAt}\n\n⏳ *Duration:* ${details.duration}`;
    } else {
        return "Song not found";
    }
}

function downloadMusic(url, outputPath, callback) {
    exec(`yt-dlp -f bestaudio "${url}" -o "${outputPath}"`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error downloading music: ${stderr}`);
            callback(error, null);
        } else {
            callback(null, outputPath);
        }
    });
}

bot.start(ctx => {
    ctx.reply("Hi! I'm Shazam bot! 👋😊\nJust give me a song title, some lyrics, or the artist's name, and I'll download the best quality version for you! 📥✨");
});

bot.command('send_audio', ctx => {
    const userId = ctx.message.from.id;
    const songName = lastSongRequested[userId];  // Retrieve the last requested song for this user

    if (songName) {
        const audioPath = `${songName}.mp3`;
        if (fs.existsSync(audioPath)) {
            ctx.replyWithAudio({ source: audioPath })
                .then(() => fs.unlinkSync(audioPath))  // Delete the file after sending
                .catch(error => ctx.reply(`Failed to send audio: ${error}`));
        } else {
            ctx.reply("Sorry, I couldn't find the audio file. Please try again.");
        }
    } else {
        ctx.reply("Please request a song first by sending the song title.");
    }
});

bot.on('text', async ctx => {
    const songName = ctx.message.text;
    const userId = ctx.message.from.id;
    lastSongRequested[userId] = songName;  // Store the last song requested by the user

    ctx.reply("⏰ Please wait");
    const songDetails = await getSongDetails(songName);
    ctx.reply(songDetails)
     .then(() => ctx.reply("📥 Downloading"))  
     .catch(error => ctx.reply(error));

    const videoInfo = await searchYouTube(songName);
    if (videoInfo) {
        const outputPath = `${songName}.mp3`;
        downloadMusic(videoInfo.link, outputPath, (error, filePath) => {
            if (error) {
                ctx.reply("🚫 Sorry, I couldn't download the song❗");
            } else {
                ctx.reply("Your audio is successfully downloaded! 😉📥\nUse /send_audio command, if you want to retrieve it.");
            }
        });
    } else {
        ctx.reply("🚫 Sorry, I couldn't find or download the song❗");
    }
});

bot.launch();
