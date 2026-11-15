# Privacy

iWantTFC Kodi (`plugin.video.tfctv`) is an unofficial, open source Kodi add-on. It has no server of its own and collects nothing: everything it keeps stays in your Kodi profile on your device.

## Trakt

**iWantTFC Kodi uses Trakt but is not endorsed or certified by Trakt.**

Trakt scrobbling is optional and off by default (setting *Scrobble what I watch to Trakt*, then *Connect to Trakt*).

- **Sign-in**: the add-on uses the device code flow. You enter a code on trakt.tv and approve the access there. The add-on never sees your Trakt password.
- **What is sent to Trakt**, only while you watch with the add-on and the setting is on: the title of the show with the season and episode numbers (or the title and year of the movie), the position in percent, and whether the playback starts, pauses, resumes or stops. The add-on also searches Trakt for the title of the show to find it.
- **What is kept on your device**: the access and refresh tokens, and the Trakt id found for each show, in `userdata.db` of the add-on profile. Nothing about your Trakt account is stored anywhere else.
- **How long**: the tokens and the show ids are kept until you disconnect, then deleted. The add-on keeps nothing else about Trakt, and no history of what was sent.
- **Disconnect and deletion**: *Disconnect from Trakt* in the settings revokes the token at Trakt and deletes the tokens and the show ids from your device. You can also remove the add-on from the connected apps of your Trakt account: the add-on then notices that its access is refused, stops using the account and forgets the tokens. Turning the setting off stops all sending. Removing the add-on deletes its profile folder and so everything it kept. What Trakt keeps (your watch history, your account) is managed on trakt.tv, where you can delete the entries or your account.
- **Limits**: scrobbles are sent at most once a second, and nothing is sent after Trakt asks to slow down until the delay it gives has passed.

Trakt processes this data under its own [privacy policy](https://trakt.tv/privacy).

## iWantTFC

To play videos the add-on signs in to your iWantTFC account with the email and password you give in its settings, and talks to `api.iwanttfc.com` and `www.iwanttfc.com`, as the website does. These requests go from your device to iWantTFC, under its own terms and privacy policy. The add-on is not affiliated with TFC, ABS-CBN or iWantTFC.

## Other data

The catalog of shows can be downloaded from the GitHub releases of this repository on first installation. GitHub sees the download request as for any file. No analytics or advertising is used.
