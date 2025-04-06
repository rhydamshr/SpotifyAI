from flask import Flask, request, render_template, session, redirect
import flask
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

# sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
#     client_id="c0b9cc3169704e82a264fb62b3ce1496",
#     client_secret="b719b1e80f164006bf4cb93da1b45164",
#     redirect_uri="http://127.0.0.1:5000/callback",
#     scope="playlist-modify-public"
# ))
SPOTIPY_CLIENT_ID = "c0b9cc3169704e82a264fb62b3ce1496"
SPOTIPY_CLIENT_SECRET = "b719b1e80f164006bf4cb93da1b45164"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:5000/callback"
genai.configure(api_key="AIzaSyBwtbSe03fdtzJrnAZR-toITKFPvCfDsCc")
modeln="gemini-2.0-pro-exp"
model = genai.GenerativeModel(model_name=modeln)
app=Flask(__name__)
app.secret_key = "meowmeow123"

@app.route("/")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="playlist-modify-public"
    )
    auth_url = sp_oauth.get_authorize_url()
    return render_template("index.html", auth_url=auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="playlist-modify-public"
    )
    session.clear()
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect("/connected")
@app.route("/connected", methods=['GET',"POST"])
def form():
    sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="playlist-modify-public"
    )
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect("/")  # No token, send back to login
    

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    sp = spotipy.Spotify(auth=token_info["access_token"])

    if request.method=="POST":
        input=request.form.get("user_input")
        print(input)
        for attempt in range(3):
            try:
                response = model.generate_content("you are a spotify playlist generator. you will be given a mood "
                    "and what you have to do is generate a list of songs that fit this mood. these songs " \
                    "will be used to make a spotify playlist later." \
                    " your playlist should include songs that strictly adhere to the mood that the user has given." \
                    "make sure to also pick newer songs within your choice " \
                    "you should first decide the mood that has been given on the bases of the prompt and then formulate a list of 50 songs that fit that mood" \
                    "if the mood is too specific then you can give lesser songs but make it at least 30" \
                    "respond with ONLY the list of songs in this format" \
                    "song1-artist 1,song-artist2,song3-artist3,song4-artist4 and so on" \
                    "MAKE SURE TO FOLLOW THIS FORMAT" \
                    "song1-artist 1,song-artist2,song3-artist3,song4-artist4" \
                    f"the mood given by the user in this case is {input}")
                break
            except Exception:
                print(f"Attempt {attempt + 1}: Timed out. Retrying...")
                time.sleep(2)
        
        songs=response.text.split(',')
        print(songs)
        track_uris = []
        for i in songs:
            song,artist=i.split('-')[0],i.split('-')[1]
            query=f'song:{song} artist:{artist}'
            result=sp.search(q=query, type='track', limit=1)
            print(result)
            items=result['tracks']['items']
            if items:
                print(items)
                track_uris.append(items[0]['uri'])
        user_id = sp.current_user()['id']
        playlist = sp.user_playlist_create(user=user_id, name=f"{input}", public=True, description="AI-generated playlist")
        sp.playlist_add_items(playlist_id=playlist['id'], items=track_uris)


        return flask.render_template('form.html', spotify_link=f"{playlist['external_urls']['spotify']}")
    return flask.render_template('form.html', spotify_link=None)
