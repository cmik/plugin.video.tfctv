[![Kodi version](https://img.shields.io/badge/kodi%20versions-19+-blue)](https://kodi.tv/)
[![GitHub release](https://img.shields.io/github/v/release/cmik/plugin.video.tfctv.svg)](https://github.com/cmik/plugin.video.tfctv/releases)

## TFC.tv add-on
Watch your favorite online Pinoy shows, movies and news directly from your TV with the TFC.tv add-on for Kodi! This add-on works with your TFC.tv account and TFC.tv website. Media contents are all properties of TFC Online and is for personal private and domestic use only. 
**This is not an official TFC.tv add-on nor released by TFC / ABS-CBN.**


## Features
- **Catalog**: browse by category, search shows and movies, and your My List. A ready-made catalog is downloaded on a first installation, then new shows are loaded as they appear.
- **Continue Watching**: episodes you stopped in the middle, with a progress bar; Kodi offers *Resume from* or *Play from beginning*.
- **My View History**: what you played, last viewed first. Played episodes are flagged as watched in every list.
- **Seasons**: shows with several seasons let you choose the season.
- **New episodes**: the add-on looks on a schedule (setting *Look for new shows and new episodes of my list every...*, 24 hours by default, 0 = never) for new shows and for the new episodes of the shows of My List, and notifies you.
- **Video quality**: choose how the stream is selected (the settings of inputstream.adaptive, ask when playback starts, or in the player) and a maximum resolution, in the add-on settings.
- **Export to the Kodi library** as `.strm` and `.nfo` files (see the Q&A).

## Requirements
- A TFC.tv / iWantTFC account and subscription. Videos are protected by Widevine DRM.
- Kodi 19 or later to install the add-on. **Playback is tested with Kodi 21 (Omega) and the current Widevine CDM**: Kodi 20.1 crashes with that CDM and an older CDM is refused by the license server.
- `inputstream.adaptive` and InputStream Helper, which Kodi installs for you.

## Add-ons
These add-ons work with iWantTFC. They are optional.

### Up Next (`service.upnext`)
When an episode starts, the add-on tells Up Next which episode follows, so that Kodi offers it at the end. Install **Up Next** from the Kodi repository; it can be turned off with the setting *Offer the next episode at the end*. Nothing is offered for movies or for the last episode of a show.

### Trakt
The add-on can scrobble what you watch to your [Trakt](https://trakt.tv) account (off by default). **iWantTFC Kodi uses Trakt but is not endorsed or certified by Trakt.**
1. In the add-on settings, turn on *Scrobble what I watch to Trakt*.
2. Click *Connect to Trakt*. A code is shown: enter it on https://trakt.tv/activate while signed in to your Trakt account and approve the access. The add-on never sees your Trakt password.
3. Play an episode or a movie: it shows as *watching* on Trakt, and in your history once you have watched most of it.

Episodes whose title gives the season and the episode (`S2 E10 - ...`) and movies are sent. Shows whose episodes are named by their day (`Ep 24th Oct 2026 - ...`) are not, because Trakt can't number them. *Disconnect from Trakt* asks Trakt to revoke the access and deletes what the add-on kept; if Trakt can't be reached at that moment, the access stays active on the Trakt side until you remove the app from the connected apps of your Trakt account. You can use your own Trakt application instead of the add-on's by giving its client id in the settings. See the [privacy notice](PRIVACY.md) for what is sent and kept.

**REPO:**
You can find my repo here where you can install TFC.tv add-on: 
SHORT LINK: https://cmik.me/repozip

**ADD-ON VERSIONS:**
The link to different versions of TFC.tv add-on since 0.44:
SHORT LINK: https://cmik.me/dDfuhJMwAt

**LATEST VERSION:** 
The latest working version can be found here : https://cmik.me/tfctvlastzip 

**SOURCE CODE:**
The source code is published on Github.
Find the source code here: https://cmik.me/tfctvSourceCode 

Do not hesitate to share your feedbacks (ideas for new features, bug issues, etc...) about this add-on so we can improve it together.

You can find some help from other users througth TFC.tv Kodi Forum thread [Release - [CMIK] TFC.tv addon - repo / updates / support](https://forum.kodi.tv/showthread.php?tid=317008) - https://forum.kodi.tv/showthread.php?tid=317008

---
## Q&A

### How do I install one of Cmik's add-on?
Add the following source in your File Manager : https://repo.cmik.me  (ex: name it "cmik.repo")
>- Go to System > add-ons > install from zip
>- Select the new source cmik.repo / [add-on] and select the latest version zip file
>- Reboot your Kodi system to apply changes to the associated service (proxy and library checker)

Or 

Simply download and install the repo from https://cmik.me/repozip
>- Install the zip on your device
>- Go to System > add-ons > install from zip and search for the Zip
>- Then opened Kodi > System > Add-ons > Install from repository> Cmik repo > \[add-on\]

See also:
>[How to install from zip file](http://kodi.wiki/view/HOW-TO:Install%20add-ons%20from%20zip%20files)
>[How to install add-ons](http://kodi.wiki/view/HOW-TO:Install%20add-ons)

For Firestick users:
>- Use the Downloader app from the amazon appstore to download the zip to the Firestick.
>- Open kodi > system > add-ons > install from zip > external > downloader > Cmik repo
>- install from repository> Cmik repo > \[add-on\]


### How to update to the latest version?
Normally, Kodi checks for updates at startup or from time to time.
You can also force Kodi to check for updates:

Go to general "Settings" > Add-on > "Seach for updates" (mine is in menu sidebar).

See also:
>[How_to_access_the_Add-on_manager (wiki)](http://kodi.wiki/view/Add-on_manager#How_to_access_the_Add-on_manager)
>[How to update your add-on (wiki)](http://kodi.wiki/view/Add-on_manager#Updating)


### I can't play a movie or an episode
>- Check your internet connection
>- Check your Kodi version and the Widevine CDM: playback needs Kodi 21 (Omega) or later with the current CDM (see *Requirements*)
>- Check that your subscription is active and that you are signed in (add-on settings)
>- If you use the optional streaming proxy (advanced settings) and see a message "The streaming proxy is not active...", reboot Kodi.
>- If the license is refused (*ACCESS_DENIED* in the log), update Kodi and the Widevine CDM.


### How can I export my TFC.tv shows in my Kodi library (export .strm and .nfo files)
>1. In the add-on general settings > Export to Library > set enable context menu to ON.
>2. Choose your personnal export path or leave it blank (it will export in the addon userdata folder by default)
>3. Set the number of last episodes to check & export (8 last episodes by default).
>4. Set the Automatic update to ON.
>5. Reboot your Kodi
>6. You can now export a show from the context menu when you are on a show list.
>7. Exit the add-on and go to Videos > Add videos... > select your "library" folder or by default the Kodi userdata directory (ex: ".../userdata/addon_data/plugin.video.tfctv/library").
[Click here](https://kodi.wiki/view/Userdata) to know the userdata directory path according to your operating system.
>7. The add-on will only export .strm and .nfo files but you will have to execute a new content check for Kodi to add new contents to its library. You can also install the add-on "Library Auto Updater" from the Kodi repository to schedule an automatic update.


### You've found a bug. How can I report it?
If you encounter anything that you think is a bug, please report it to the add-on github repo (https://github.com/cmik/plugin.video.tfctv/issues). 
Do not hesitate to give more details about your issue: 
>- your device & plateform version
>- your add-on version
>- how to reproduce the bug or the error
>- the corresponding error message in Kodi.log file (beforehand, enable Debug mode on the add-on advanced settings and set debug level at least to INFO)
>- the URL link to your kodi.log pasted file

To simply export and share your log file, I recommend you to use the Kodi Logfile Uploader add-on (https://kodi.wiki/view/Add-on:Kodi_Logfile_Uploader)).



Find more info at https://addons.cmik.me

Enjoy!

---

If you like my work, you can support me by making a donation:
- [Donate with Paypal](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=Q8DETSCYJDR7E&currency_code=EUR&source=url)
![Donate with Paypal](https://www.cmik.me/img/donate_paypal.png)
