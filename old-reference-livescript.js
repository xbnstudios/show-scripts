#!/usr/local/bin/node

/* =====================
	Script Variables
===================== */

// Ping the chat/tweet URLs?
var pingChat = true;
var pingGraphics = false;
var pingTweet = true;

// The location of the playlist .txt files
var playlistsDir = '/media/storage/tls/playlists/';

// The location of the current track for IceCast
var npFile = '/media/storage/tls/songnp.txt';

// The urls for chat and tweet scripts
var chatURL = 'http://localhost/chatping.php?data=';
var graphicsURL = 'http://localhost/graphics/update-track.php?song=';
var tweetURL = '';

// The delay between checks (in seconds)
var delay = 3;

// A cache of the last song
var lastSong = '';

// Internal use, DO NOT TOUCH
var init, updateLastSong, interval;

/* =================
	Load Modules
================= */

var cp = require('child_process');
var http = require('http');
var fs = require('fs');

/* ==========================
	Singleton Enforcement
========================== */

// Check for other instances of this script
var pidof = cp.exec('pidof -x tracklist.js', function(error, stdout){
	// Get the list of pids
	var pids = stdout.toString().trim().split(/\s+/);
	
	// Only one instance, nothing to worry about
	if(pids.length > 1){
		// Loop through each pid
		pids.forEach(function(pid){
			// If it's not this pid, kill it
			if(pid != process.pid){
				console.log('Other instance found ('+pid+'), killing...');
				process.kill(pid, 'SIGINT');
			}
		});	
	}
	
	init();
});

/* =================
	Script Logic
================= */

// The function to check for and update the latest song
updateLastSong = function(){
	// Scan the playlist directory and get just the Playlist_ files
	var playlistFiles = fs.readdirSync(playlistsDir).filter(function(file){
		return file.indexOf('Playlist_') === 0;
	});
	
	// Get the latest playlist file
	var latestFile = playlistFiles.pop();
	
	// Read the playlist and split into lines
	var playlist = fs.readFileSync(playlistsDir + latestFile, {
		encoding: 'binary' // Apparently works best; sometime it's in utf8, sometimes latin1
	}).trim().split(/[\r\n]+/);
	
	// Get the last song in the list (remove "## " prefix)
	var song = playlist.pop().replace(/^\d+\s/, '');
	
	// Skip if it starts with xbn# or is the same as before
	if(song.match(/^xbn\d/i) || lastSong == song) return false;
	
	// Update lastSong
	lastSong = song;
	
	return true;
};

// The actual code to run when ready
init = function(){
	console.log('Starting...');
	
	// Fetch the last song
	updateLastSong();
	console.log('Last song was: ' + lastSong);
	
	// Setup the check interval
	interval = setInterval(function(){
		// Check if there's a new song, skip if not
		if(!updateLastSong()) return;
		
		console.log('New song detected: ' + lastSong);
		
		var tweetPrefix = fs.readFileSync('/media/storage/tls/prefix.txt').toString();
		
		// Escape for URL and clean loading purposes
		var escapedSong = encodeURIComponent(lastSong);
		var escapedMsg = encodeURIComponent(tweetPrefix + ' ' + lastSong);
		
		if(pingChat){
			console.log('Pinging chat script...');
			http.request(chatURL + escapedMsg).end();
		}
		
		if(pingGraphics){
			console.log('Pinging graphics script...');
			http.request(graphicsURL + escapedMsg).end();
		}
		
		if(pingTweet){
			console.log('Pinging tweet script...');
			http.request(tweetURL + escapedMsg).end();
		}
		
		console.log('Writing to ' + npFile);
		fs.writeFile(npFile, lastSong, {
			encoding: 'utf8',
			mode: 0644
		});
	}, delay * 1000);
};

/* =================
	Quit Handler
================= */

process.on('SIGINT', function(){
	console.log('\nQuitting...');
	clearInterval(interval);
	process.exit();
});