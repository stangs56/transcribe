# standard library
import os
import argparse
import sys
import pdb

from pathlib import Path
from datetime import datetime

#dependencies
# AWS
import boto3 #pip install boto3

# Word docx
import docx #pip install python-docx
from docx.shared import Inches

# Imports the Google Cloud client library
# pip install google-cloud-speech
#from google.cloud import speech
import google.cloud.speech_v1p1beta1
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types

# pip install google-cloud-storage
import google.cloud.storage


def main():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('file', help='File to upload and transcribe')

    parser.add_argument('--bucket', '-b', default='prof-resp-trans',
        help='What bucket to store file to')
    parser.add_argument('--output', '-o')
    parser.add_argument('--region', '-r', default='us-east-1')
    parser.add_argument('--back-end', '-be', default='google')
    parser.add_argument('--show-parameters', '-s', action='store_true')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--paragraph-break', '-pb', default=60, type=int,
        help='The number of seconds between paragraphs')

    args = parser.parse_args()

    if args.show_parameters:
        print(args)

    fp = Path(args.file)

    if not fp.exists():
        print('Error: path does not exist')
        return

    file_list = [ fp ]

    if fp.is_dir():
        file_list = fp.rglob('*.wav'):

    for cur in file_list:
        new_file = cur.with_suffix('.docx')

        if new_file.exists():
            print('Transcript already exists: {}'.format(new_file.resolve()))
            return

        content = google_transcribe_file(cur)

        file_name = str(new_file)
        write_document(file_name, content, args.paragraph_break)

        new_print('Transcript saved to {}'.format(file_name))



def google_transcribe_file(fp, bucket_name='prof-resp-trans'):
    storage_client = google.cloud.storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    client = google.cloud.speech_v1p1beta1.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        language_code='en-US',
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True)

    blob = bucket.blob(fp.name)

    if not blob.exists():
        new_print('Uploading File: {}'.format(fp.name))

        blob.upload_from_filename(str(fp.resolve()))

        new_print('Finished Uploading: {}'.format(fp.name))
    else:
        new_print('File already uploaded: {}'.format(fp.name))

    new_print('Starting transcription...')

    audio = types.RecognitionAudio(uri='gs://{}/{}'.format(bucket_name, fp.name))

    response = client.long_running_recognize(config, audio)
    results = response.result()

    new_print('Transciption finished')

    return results


def aws_transcribe_file(fp, bucket_name=None):
    s3_client         = boto3.client('s3', region_name=args.region)
    transcribe_client = boto3.client('transcribe', region_name=args.region)

    s3_client.upload_file(fp.resolve(), bucket, fp.name)

def write_document(file_name, content, paragraph_break):
    document = docx.Document()

    sec = document.sections[-1]
    sec.left_margin = Inches(0.5)
    sec.right_margin = Inches(0.5)

    table = document.add_table(0,2)

    last_break_time = 0
    r = table.add_row().cells
    r[0].text = '0:00'

    r[0].width = Inches(0.5)
    r[1].width = Inches(7)

    for res in content.results:
        cur = res.alternatives[0].transcript
        start_time = res.alternatives[0].words[0].start_time.seconds

        if start_time > last_break_time + paragraph_break:
            r = table.add_row().cells

            r[0].text = '{}:{:02}'.format(start_time // 60, start_time % 60)
            r[0].width = Inches(0.5)

            last_break_time = start_time + paragraph_break

        r[1].text += str(cur)
        r[1].width = Inches(7)

    document.save(file_name)

def new_print(out):
    print('[{}] : {}'.format(datetime.now(), out))


if __name__ == '__main__':
    main()
