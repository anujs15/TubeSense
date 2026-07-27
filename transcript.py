import os
import random
import subprocess
import tempfile
import time

import requests
import streamlit as st
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from youtube_transcript_api import YouTubeTranscriptApi

from youtube import extract_video_id


def fetch_transcript(video_id, target_lang="auto", use_ytdlp=True):
    transcript_text = None
    if "youtube_proxies" in st.secrets:
        proxy_list = list(st.secrets.get("youtube_proxies", {}).values())
    else:
        proxy_list = [None]

    for proxy_url in random.sample(proxy_list, len(proxy_list)):
        try:
            if proxy_url:
                session = requests.Session()
                session.proxies.update({"http": proxy_url, "https": proxy_url})
                from youtube_transcript_api import _api

                _api.requests = session

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            if target_lang == "auto":
                base = transcript_list.find_generated_transcript(["en"])
                transcript = base.fetch()
            elif target_lang == "hi":
                base = transcript_list.find_generated_transcript(["en"])
                transcript = base.translate("hi").fetch()
            elif target_lang == "en":
                base = transcript_list.find_generated_transcript(["en"])
                transcript = base.fetch()
            else:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[target_lang])

            if transcript:
                transcript_text = " ".join([t["text"] for t in transcript if t["text"].strip()])
                return transcript_text
        except Exception:
            time.sleep(1)

    if use_ytdlp:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")
                cmd = [
                    "yt-dlp",
                    "--skip-download",
                    "--write-auto-subs",
                    "--sub-lang",
                    "en",
                    "-o",
                    output_template,
                    f"https://www.youtube.com/watch?v={video_id}",
                ]
                subprocess.run(cmd, capture_output=True, check=True)

                for file_name in os.listdir(tmp_dir):
                    if file_name.endswith(".vtt"):
                        vtt_file = os.path.join(tmp_dir, file_name)
                        lines = []
                        with open(vtt_file, "r", encoding="utf-8") as vf:
                            for line in vf:
                                if line.strip() and not line[0].isdigit() and "-->" not in line:
                                    lines.append(line.strip())
                        if lines:
                            return " ".join(lines)
        except Exception as exc:
            st.warning(f"yt-dlp fallback failed: {exc}")

    return None


def summarize_youtube_video(url, llm, target_lang="auto"):
    try:
        video_id = extract_video_id(url)
        if not video_id:
            return "Could not extract a valid video ID."

        text = fetch_transcript(video_id, target_lang)
        if not text:
            return "Could not retrieve a transcript or captions."

        docs = [Document(page_content=text)]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        split_docs = text_splitter.split_documents(docs)

        if target_lang == "hi":
            instruction = "इस वीडियो ट्रांसक्रिप्ट का संक्षेप हिंदी में लिखिए। अगर मूल पाठ अंग्रेज़ी में है तो पहले अनुवाद कर संक्षेप हिंदी में लिखें।"
        elif target_lang == "en":
            instruction = "Summarize this video transcript in English."
        else:
            instruction = "Summarize this video transcript in its original language."

        prompt_template = PromptTemplate(
            template=f"""{instruction}

Transcript:
{{text}}

Summary:""",
            input_variables=["text"],
        )

        chain = LLMChain(llm=llm, prompt=prompt_template)
        combined_text = " ".join([d.page_content for d in split_docs])
        return chain.run({"text": combined_text})
    except Exception as exc:
        return f"Error while summarizing: {exc}"