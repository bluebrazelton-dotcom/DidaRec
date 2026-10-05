# DidaRec

A free, open-source screen recorder by DidaWorks. Runs entirely in your browser — no account, no server, no watermark, no time limits.

**Crash-resilient by design:** Every second of your recording is saved to disk as it happens. If your browser crashes at minute 58 of a lecture, you lose about one second of video, because everything else is already saved.

## Features

- Record your screen, webcam, and microphone
- Webcam picture-in-picture overlay — draggable, resizable, with rectangle/square/circle shapes
- Pause and resume recording
- **Change screen while paused** — pause, pick a different screen or window to share, resume. The swap never gets recorded; the saved file plays as one continuous take
- **Stop sharing pauses, it doesn't end** — if you end the share from the browser's own "Stop sharing" bar, the recording pauses. Choose Change screen and resume to carry on in the same file, or Stop & save
- A screen or window with a different shape is fitted into the picture with black bars, never stretched
- Recording quality presets and microphone noise suppression
- Crash-resilient recording — survives browser crashes, tab closures, power loss
- Continue Recording — pick up where a crash left off and stitch segments automatically
- Automatic recovery of interrupted recordings on reopen
- A "Recording kept — not saved yet" banner whenever footage is waiting to be saved, so saving never needs a page refresh
- **Review pane with take controls** — stop into a review screen instead of saving immediately, then:
  - **Redo last take** — one click discards your most recent segment and re-arms recording from right before it, so a botched take costs you nothing but the botched part
  - **Re-record from a point you scrub to**, or type a time (`m:ss`, like `1:30`, or `h:mm:ss` for longer recordings) and cut from there directly
  - Save as is, or discard the recording entirely
- **Caption editor** — open a saved `.webm` recording, add or import captions (`.vtt`/`.srt`), edit them against playback, and export a sidecar caption file. Captions are never burned into the video — they save as their own small file next to it, and the two travel together in the same folder (course sites and video players pick captions up automatically from a same-name file). Because it opens saved files, you save your recording first, then open it in the caption editor to caption it
- Camera and microphone device selection, with real device names shown once permission is granted
- Saves directly to your computer — no upload, no cloud
- Works in **Chrome/Edge** (recommended) and **Firefox**

## How it works

Most screen recorders hold your entire recording in memory and only save it when you click Stop. That's why the horror stories all sound the same: an hour of recording, a crash, nothing to show for it.

DidaRec writes each second of video to persistent storage the moment it's recorded. There's nothing waiting in memory to lose.

## Browser support

**Use Chrome or Edge if you can.** DidaRec is built and tested Chrome-first, and Edge (already on every Windows computer) works the same way. Firefox is supported, with the limits listed below.

- **Chrome/Edge (recommended):** uses the File System Access API. When you stop a recording, a normal save dialog opens; you choose where the file goes, and DidaRec writes it there and confirms the write. Computer audio can be recorded by ticking "Also share audio" in the share picker.
- **Firefox (supported, with limits):**
  - **Saving is a download.** Firefox doesn't implement that API, so the finished file arrives as a normal browser download. Since a page can't confirm a download succeeded, DidaRec shows a "Downloaded — did it arrive?" bar; click "It's there — all set" once you've checked your Downloads folder, or "It didn't arrive — keep my recording" to keep it safely stored for another attempt.
  - **No computer audio** without extra setup — see "System audio on Firefox" below.
  - **Re-recording from a point in the first several seconds of a take isn't available.** Choosing a time that early offers to start the take over instead. Later points work normally.

Either way, the crash-resilience story is the same underneath: your recording is written to your browser's storage in small pieces the whole time, and the save step assembles and hands off what's already safe.

## System audio on Firefox

Firefox cannot capture your computer's system or tab audio from a web page — it currently ignores the browser's request for that audio track entirely (this is an upstream Firefox limitation, tracked publicly as Bugzilla bug 1541425, open since 2019). It isn't something DidaRec can work around from inside the app. DidaRec already asks for system audio every time you share a screen, so if Firefox ever ships support for this, recording system audio in Firefox will start working with no update to DidaRec needed.

Until then, here's how to get system audio into a Firefox recording:

**Route system audio in as your "microphone."** DidaRec already lets you pick which microphone to record, and a loopback input shows up in that same list looking just like a mic:

- **Windows "Stereo Mix"** — some sound drivers expose this built in (right-click the speaker icon → Sounds → Recording tab → enable Stereo Mix if you see it). If it's there, select it as your microphone in DidaRec.
- **VB-Audio Virtual Cable (VB-Cable)** — a free virtual loopback device if your driver doesn't offer Stereo Mix. Set your system output to the cable, then select the cable as your microphone in DidaRec.
- **Need your real mic AND system audio at the same time?** A simple loopback device can only carry one signal. Use **VoiceMeeter** (free) to mix your microphone and your system audio together into one virtual output, then select that mixed output as your "microphone" in DidaRec.

**Watch for echo.** If the loopback device is capturing the same audio you're actively listening to out loud (speakers, not headphones), your recording can pick up doubled or echoing sound. Fix it by listening on headphones, or by routing your monitoring through a different output than the one being looped back (VoiceMeeter handles this cleanly).

**Chrome/Edge don't need any of this.** When you share a screen or tab, tick "Also share audio" (or "Share tab audio," depending on what you're sharing) right in the browser's share picker, and DidaRec records it.

If a screen share ever lands with no audio, DidaRec shows a one-time reminder the first time it happens, worded for whichever browser you're using.

## Requirements

- Chrome or Edge 86 or newer (recommended; DidaRec is developed and tested against current Chrome), or Firefox 153 or newer (earlier versions are untested)
- HTTPS (required for screen capture APIs) — use the hosted version or run locally with a dev server

## Usage

Use it right now at [bluebrazelton-dotcom.github.io/DidaRec](https://bluebrazelton-dotcom.github.io/DidaRec/), or clone [the repo](https://github.com/bluebrazelton-dotcom/DidaRec) and serve it locally.

## License

MIT — see [LICENSE](LICENSE).

## Part of DidaWorks

DidaRec is part of the DidaWorks productivity suite.
