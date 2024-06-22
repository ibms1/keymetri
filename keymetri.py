import streamlit as st
from pytrends.request import TrendReq
from googleapiclient.discovery import build
import pandas as pd
import datetime
import time
import google.generativeai as genai

# Directly specify the API keys (for testing purposes only)
GOOGLE_API_KEY = 'AIzaSyDbMa95_4sF1AtHpDOxKDRov7mRh0ldcqY'
YOUTUBE_API_KEY = 'AIzaSyCMsj5PfQu_SBNvVj_ge1qVUKbwKA0n2xs'

# Initialize Generative AI Model
model = genai.GenerativeModel('gemini-pro')

# CSS مخصص لإخفاء الروابط عند تمرير الفأرة
hide_links_style = """
    <style>
    a {
        text-decoration: none;
        color: inherit;
        pointer-events: none;
    }
    a:hover {
        text-decoration: none;
        color: inherit;
        cursor: default;
    }
    </style>
    """
st.markdown(hide_links_style, unsafe_allow_html=True)

st.title('Youtube Keywords Analysis Tool')

keyword = st.text_input('Enter a keyword:')
if st.button('Start Keyword Analyze'):
    with st.spinner('Keyword Analyze...'):
        search_interest = {'last_day': 0, 'last_week': 0, 'last_month': 0}
        try:
            # Google Trends data
            pytrends = TrendReq(hl='en-US', tz=360)
            pytrends.build_payload([keyword], geo='')

            # Adding delay to avoid hitting the rate limit
            time.sleep(5)

            trends_last_day = pytrends.interest_over_time().tail(1)
            trends_last_week = pytrends.interest_over_time().tail(7)
            trends_last_month = pytrends.interest_over_time().tail(30)

            search_interest = {
                'Last Day': trends_last_day[keyword].sum(),
                'Last Week': trends_last_week[keyword].sum(),
                'Last Month': trends_last_month[keyword].sum()
            }

            st.subheader('Search Volume')
            st.table(pd.DataFrame(search_interest, index=["Metrics"]))

        except Exception as e:
            st.error(f"An Error While Analyzing Keyword , please Try Again  Later")

        try:
            # YouTube Data API for videos
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

            videos = []
            next_page_token = None
            while True:
                search_response = youtube.search().list(
                    q=keyword,
                    order='date',
                    type='video',
                    publishedAfter=(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat(),
                    part='snippet',
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()

                for item in search_response['items']:
                    try:
                        video_id = item['id']['videoId']
                        video_response = youtube.videos().list(
                            part='snippet, statistics',
                            id=video_id
                        ).execute()

                        statistics = video_response['items'][0]['statistics']
                        videos.append({
                            'title': item['snippet']['title'],
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'videoId': video_id,
                            'viewCount': int(statistics.get('viewCount', 0)),
                            'publishedAt': item['snippet']['publishedAt']
                        })

                    except Exception as e:
                        st.warning(f"An Error While Analyzing Keyword , please Try Again  Later")

                    # Add a delay to avoid hitting API rate limits
                    time.sleep(1)  # Delay of 1 second

                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break

            df_videos = pd.DataFrame(videos)
            df_videos['publishedAt'] = pd.to_datetime(df_videos['publishedAt']).dt.tz_convert('UTC')

            now = pd.Timestamp.now(tz='UTC')
            views_last_24h = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('1 day')]['viewCount'].sum()
            views_last_7d = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('7 days')]['viewCount'].sum()
            views_last_month = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('30 days')]['viewCount'].sum()

            video_count_last_24h = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('1 day')].shape[0]
            video_count_last_7d = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('7 days')].shape[0]
            video_count_last_month = df_videos[df_videos['publishedAt'] >= now - pd.Timedelta('30 days')].shape[0]

            youtube_views_data = {
                'Last Day': views_last_24h,
                'Last Week': views_last_7d,
                'Last Month': views_last_month
            }

            youtube_video_count_data = {
                'Last Day': video_count_last_24h,
                'Last Week': video_count_last_7d,
                'Last Month': video_count_last_month
            }

            st.subheader('YouTube Videos Views For Keyword')
            st.table(pd.DataFrame(youtube_views_data, index=["Metrics"]))

            st.subheader('YouTube Videos Uploaded For Keyword')
            st.table(pd.DataFrame(youtube_video_count_data, index=["Metrics"]))

            st.subheader('YouTube Channels For Keyword')
            # YouTube Data API for channels
            channels = []
            next_page_token = None
            while True:
                search_response = youtube.search().list(
                    q=keyword,
                    type='channel',
                    part='snippet',
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()

                for item in search_response['items']:
                    try:
                        channel_id = item['snippet']['channelId']
                        channel_response = youtube.channels().list(
                            part='statistics',
                            id=channel_id
                        ).execute()

                        statistics = channel_response['items'][0]['statistics']
                        channels.append({
                            'channelId': channel_id,
                            'subscriberCount': int(statistics.get('subscriberCount', 0)),
                            'videoCount': int(statistics.get('videoCount', 0)),
                            'viewCount': int(statistics.get('viewCount', 0))
                        })

                    except Exception as e:
                        st.warning(f"An Error While Analyzing Keyword , please Try Again  Later")

                    # Add a delay to avoid hitting API rate limits
                    time.sleep(1)  # Delay of 1 second

                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break

            df_channels = pd.DataFrame(channels)

            total_channels = df_channels.shape[0]
            total_subscribers = df_channels['subscriberCount'].sum()
            total_videos = df_channels['videoCount'].sum()

            youtube_channels_data = {
                'Total Channels': total_channels,
                'Total Subscribers': total_subscribers,
                'Total Videos': total_videos
            }

            st.table(pd.DataFrame(youtube_channels_data, index=["Metrics"]))

            st.subheader('Top 10 Videos')

            if not df_videos.empty:
                top_10_videos_table = pd.DataFrame({
                    'Rank': range(1, 11),
                    'Title': df_videos.head(10)['title'],
                    'Thumbnail': df_videos.head(10)['thumbnail'],
                    'Views': df_videos.head(10)['viewCount']
                })

                # Format thumbnail column with HTML <img> tags for displaying images
                def make_thumbnail_img(url):
                    return f'<img src="{url}" width="200">'

                top_10_videos_table['Thumbnail'] = top_10_videos_table['Thumbnail'].apply(make_thumbnail_img)

                # Use st.markdown to render HTML content
                for i, row in top_10_videos_table.iterrows():
                    st.markdown(f"**{row['Rank']}. {row['Title']}**")
                    st.markdown(row['Thumbnail'], unsafe_allow_html=True)
                    st.markdown(f"Views: {row['Views']}")

            else:
                st.warning("No videos found for the given keyword.")

        except Exception as e:
            st.error(f"An Error While Analyzing Keyword , please Try Again  Later")

        try:
            # Use genai to generate recommendations
            st.subheader('AI Analyzing Report')
            titles = [video['title'] for video in videos[:10]]
            analysis_prompt = (f"Analyze search interest ({search_interest}), video views ({views_last_24h}, {views_last_7d}, {views_last_month}), "
                            f"and video uploads ({video_count_last_24h}, {video_count_last_7d}, {video_count_last_month}). "
                            f"Provide an opinion on search volume and competition level."
                            f"Then, suggest 5 catchy, click-baity, SEO-optimized titles based on the keyword '{keyword}'.")
            
            response = model.generate_content(analysis_prompt).text

            st.write(response)

        except Exception as e:
            st.error(f"An Error While Analyzing Keyword , please Try Again  Later")
