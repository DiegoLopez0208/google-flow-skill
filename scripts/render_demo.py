"""Create a 40s silent launch demo from reviewed, previously recorded footage.

Requires FFmpeg with drawtext and a font file. No live Flow generation occurs.
Source directory: the existing demo's public/ folder, with start.png,
generated.mp4, flow_prompt_crop.mp4, flow_settings_crop.mp4 and flow_card.mp4.
"""

import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--font", required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    font = args.font.replace("\\", "/").replace(":", r"\:")

    def text(name, value, y, size=40, color="0xf2f0e9", x="(w-text_w)/2"):
        (args.out / (name + ".txt")).write_text(value, encoding="utf-8")
        return (f"drawtext=fontfile='{font}':textfile='{name}.txt':"
                f"fontsize={size}:fontcolor={color}:x={x}:y={y}")

    scenes = [
        (5, "generated.mp4", "An agent. A script. Google Flow.",
         ["Generate images and videos", "from an ordered scene script."], "Previously generated output"),
        (6, None, "Give your agent the script",
         ["The CLI runs the jobs in order.", "Review files and the batch report."], "Editorial workflow overview"),
        (6, "start.png", "Reuse an image",
         ["Use references for visual guidance", "or pin a first frame."], "Reference image + recorded Flow panel"),
        (6, "flow_settings_crop.mp4", "Check before generating",
         ["Read the balance and batch estimate.", "Flow shows a video price quote."], "Recorded quote - prices can change"),
        (6, "flow_card.mp4", "Wait. Download. Review.",
         ["Generation runs in Chrome.", "Downloads prefer HTTP."], "Previously recorded Flow progress"),
        (6, "generated.mp4", "Inspect the result",
         ["References help continuity.", "They cannot guarantee it."], "Previously generated output"),
        (5, None, "Install Google Flow Skill",
         ["Free, open-source code.", "Flow generation may cost credits."], "Python 3.10+ and Google Chrome required"),
    ]
    parts = []
    timeline = []
    at = 0
    for index, (duration, media, title, captions, note) in enumerate(scenes):
        cmd = [args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
        if media:
            if media.endswith(".png"):
                cmd += ["-loop", "1"]
            else:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", str(args.source / media)]
            graph = ("[0:v]scale=920:1180:force_original_aspect_ratio=decrease,"
                     "pad=1080:1920:(ow-iw)/2:310:color=0x101410,setsar=1[base]")
            if index == 2:
                cmd += ["-stream_loop", "-1", "-i", str(args.source / "flow_prompt_crop.mp4")]
                graph += ";[1:v]scale=940:-2[panel];[base][panel]overlay=(W-w)/2:1210:shortest=1[composed]"
                base = "[composed]"
            else:
                base = "[base]"
        else:
            cmd += ["-f", "lavfi", "-i", f"color=c=0x101410:s=1080x1920:r=30:d={duration}"]
            graph, base = "", "[0:v]"
        filters = [
            "drawbox=x=0:y=0:w=iw:h=6:color=0xbfa47b:t=fill",
            text(f"brand{index}", "GOOGLE FLOW SKILL  /  2.3.0", 80, 32, "0xbfa47b"),
            text(f"title{index}", title, 165, 52),
        ]
        if media is None:
            filters.append("drawbox=x=70:y=480:w=940:h=670:color=0x1b241f:t=fill")
            if index == 1:
                lines = ["Your scene script", "↓", "Ordered image / video jobs", "↓", "Downloaded files + batch report"]
                for line_index, line in enumerate(lines):
                    filters.append(text(f"flow{line_index}", line, 560 + line_index * 105, 43))
            else:
                lines = ["npx skills add", "DiegoLopez0208/google-flow-skill", "--skill google-flow", "", "The manual installs the CLI."]
                for line_index, line in enumerate(lines):
                    filters.append(text(f"install{line_index}", line, 565 + line_index * 105, 40))
        filters += [text(f"note{index}", note, 1490, 29, "0xb2b9af")]
        for caption_index, caption in enumerate(captions):
            filters.append(text(f"cap{index}_{caption_index}", caption, 1570 + caption_index * 65, 41))
        filters += [
            "drawbox=x=60:y=1770:w=960:h=2:color=0xbfa47b:t=fill",
            text(f"repo{index}", "github.com/DiegoLopez0208/google-flow-skill", 1810, 35, "0xbfa47b"),
        ]
        if graph:
            graph += ";"
        graph += base + ",".join(filters) + "[out]"
        name = f"part-{index}.mp4"
        cmd += ["-filter_complex", graph, "-map", "[out]", "-an", "-t", str(duration),
                "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", name]
        subprocess.run(cmd, cwd=args.out, check=True)
        parts.append(f"file '{name}'")
        timeline.append({"start": at, "duration": duration, "title": title, "source": media})
        at += duration
        print(f"Rendered scene {index + 1}/{len(scenes)}", flush=True)
    (args.out / "concat.txt").write_text("\n".join(parts))
    subprocess.run([args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                    "-safe", "0", "-i", "concat.txt", "-c", "copy", "-movflags", "+faststart",
                    "google-flow-demo-en.mp4"], cwd=args.out, check=True)
    (args.out / "timeline.json").write_text(json.dumps(timeline, indent=2))
    print(args.out / "google-flow-demo-en.mp4")


if __name__ == "__main__":
    main()
