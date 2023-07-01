from flask import Flask, request, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from HCR2Reader import process_images, get_score_mapping
import pandas as pd
import os
import threading
from io import BytesIO

app = Flask(__name__)
lock = threading.Lock()  # Create a threading lock object
processing = False  # Flag to indicate if processing is currently in progress

@app.route('/')
def index():
    return render_template('index.html', processing=processing)  # Pass the processing flag to the template

@app.route('/upload', methods=['POST'])
def upload():
    global processing  # Access the processing flag as a global variable

    with lock:
        if processing:
            return render_template('busy.html')  # Render a template indicating the server is busy

        processing = True  # Set the processing flag to indicate processing has started

        try:
            if 'file' not in request.files:
                processing = False  # Set the processing flag to indicate processing has finished
                return 'No file part in the request.', 400

            files = request.files.getlist('file')

            df = pd.DataFrame()

            for file in files:
                file_bytes = file.read()  # Read the file as bytes

                # Process the image from the bytes using BytesIO
                image = BytesIO(file_bytes)

                processed_df = process_images(image)  # Process the image directly from memory
                df = pd.concat([df, processed_df], ignore_index=True)

            if not df.empty:
                replacements = {
                    's': '5',
                    'S': '5',
                    'g': '9',
                    'H': '4',
                    'i': '1',
                    'I': '1',
                    'l': '1',
                    'j': '1',
                    'z': '2',
                    'Z': '2'
                }

                for character, replacement in replacements.items():
                    df['points'] = df['points'].str.replace(character, replacement, regex=False)

                df['points'] = pd.to_numeric(df['points'], errors='coerce')
                df['points'].fillna(0, inplace=True)

                df['expected_position'] = df.index + 1

                mean_score = df.loc[df['points'] > 4000, 'points'].mean()

                df = df.sort_values(by=['points'], ascending=False)

                df['expected_position'] = df.index + 1

                condition_high_score = (df['points'] > 2 * mean_score)
                condition_wrong_position = (abs(df.reset_index().index + 1 - df['expected_position']) > 1)

                df.loc[condition_high_score & condition_wrong_position, 'points'] = 333

                df['position'] = range(1, len(df) + 1)
                score_mapping = get_score_mapping()
                df['score'] = df['position'].map(score_mapping).fillna(0)

                df = custom_sort(df)

                df.to_csv('temp.csv', index=False)

            # After processing the files, reset the processing flag
            processing = False

            # Redirect to the download page
            return redirect(url_for('download'))
        
        except Exception as e:
            # Handle the exception here (e.g., log the error, display an error message)
            # ...

            # Reset the processing flag in case of an error
            processing = False

            # Redirect to an error page or display an error message
            return render_template('error.html', error=str(e))
        
        finally:
            # Ensure the processing flag is always reset
            processing = False

@app.route('/download', methods=['GET'])
def download():
    # Render a template with a download link
    return render_template('download.html')

@app.route('/getfile', methods=['GET'])
def getfile():
    # Serve the file over HTTP
    return send_file('temp.csv', as_attachment=True)

def custom_sort(df):
    df = df.copy()
    df['original_index'] = df.index
    if df.empty:
        return df  # Return the empty DataFrame if there are no rows
    # Check if any rows have points equal to 333
    if (df['points'] == 333).any():
        # Get the original index of the player to be moved
        moved_player_rows = df[df['points'] == 333]
        moved_player_index = moved_player_rows['original_index'].values[0]
        # increment the position of the players that are above or equal to the moved player
        df.loc[df['original_index'] <= moved_player_index, 'position'] += 1
        # set the position of the moved player
        df.loc[df['points'] == 333, 'position'] = df.loc[df['points'] == 333, 'expected_position']
        df.sort_values(['position', 'original_index'], inplace=True)
        df['position'] = range(1, len(df) + 1)
        score_mapping = get_score_mapping()
        df['score'] = df['position'].map(score_mapping).fillna(0)

    # Drop the helper columns
    df.drop(['expected_position', 'original_index'], axis=1, inplace=True)
    return df

if __name__ == "__main__":
    # Get the PORT from the environment variable
    port = int(os.getenv('PORT', 8080))

    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)