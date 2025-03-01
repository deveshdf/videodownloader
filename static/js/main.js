function getStreams() {
    const url = document.getElementById('url').value;
    const formData = new FormData();
    formData.append('url', url);

    fetch('/get_streams', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('video-info').style.display = 'block';
            document.getElementById('video-title').textContent = data.title;
            document.getElementById('thumbnail').src = data.thumbnail;
            
            const videoStreams = document.getElementById('video-streams');
            const audioStreams = document.getElementById('audio-streams');
            
            videoStreams.innerHTML = '';
            audioStreams.innerHTML = '';

            data.streams.video.forEach(stream => {
                const button = document.createElement('button');
                button.className = 'download-button';
                button.textContent = `${stream.resolution} - ${stream.filesize}`;
                button.onclick = () => downloadStream(url, stream.itag, 'mp4');
                videoStreams.appendChild(button);
            });

            data.streams.audio.forEach(stream => {
                const button = document.createElement('button');
                button.className = 'download-button';
                button.textContent = `${stream.abr} - ${stream.filesize}`;
                button.onclick = () => downloadStream(url, stream.itag, 'mp3');
                audioStreams.appendChild(button);
            });
        } else {
            alert('Error: ' + data.message);
        }
    });
}

function downloadStream(url, itag, ext) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/download';

    const urlInput = document.createElement('input');
    urlInput.type = 'hidden';
    urlInput.name = 'url';
    urlInput.value = url;

    const itagInput = document.createElement('input');
    itagInput.type = 'hidden';
    itagInput.name = 'itag';
    itagInput.value = itag;

    const extInput = document.createElement('input');
    extInput.type = 'hidden';
    extInput.name = 'ext';
    extInput.value = ext;

    form.appendChild(urlInput);
    form.appendChild(itagInput);
    form.appendChild(extInput);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
} 