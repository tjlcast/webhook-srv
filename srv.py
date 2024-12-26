from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)
current_directory = os.getcwd()

@app.route('/gitlab-webhook', methods=['POST'])
def gitlab_webhook():
    # 获取 Webhook 数据
    payload = request.json

    # 确认事件类型
    if payload.get("ref_type") == "tag":
        project_name = payload["repository"]["name"]
        tag_name = payload["ref"].split('/')[-1]
        repository_path = payload["repository"]["ssh_url"]
        repo_url = payload["repository"]["html_url"]

        print(f"New Tag Created: {tag_name} in {project_name}")

        try:
        	subprocess.run(["rm", "-rf", f"{project_name}"], cwd=current_directory, check=True)
        except FileNotFoundError as e:
          print("File not found.")
        
        # Clone or update the repository locally (for simplicity)
        repo_dir = f"{current_directory}/{project_name}"
        subprocess.run(["git", "clone", repository_path, repo_dir], cwd=current_directory, check=True)
        #subprocess.run(["git", "clone", "--depth", "1", repository_path, repo_dir], cwd="/home/jialtang/apps/webhook-srv", check=True)
        #subprocess.run(["git", "-C", repo_dir, "fetch", "--tags"], check=True)
        subprocess.run(["git", "fetch", "--tags"], cwd=repo_dir, check=True)

        # 获取所有 Tag，按时间排序
        tags = subprocess.check_output(
            ["git", "for-each-ref", "--sort=-creatordate", "--format", "'%(refname:short)'", "refs/tags"],
            cwd=repo_dir,
            universal_newlines=True
        ).splitlines()
        tags = [tag.strip("'") for tag in tags]

        # 找到前一个 Tag
        prev_tag = None
        for i, tag in enumerate(tags):
            if tag == tag_name and i + 1 < len(tags):
                prev_tag = tags[i + 1]
                break

        if not prev_tag:
            prev_tag = subprocess.check_output(
                ["git", "rev-list", "--max-parents=0", "HEAD"],
                cwd=repo_dir,
                universal_newlines=True
            ).strip()

        # 获取新 Tag 和前一个 Tag 之间的 Commit 信息
        commits = subprocess.check_output(
#            ["git", "log", f"{prev_tag}..{tag_name}", "--oneline"],
		   ["git", "log", f"{prev_tag}..{tag_name}", "--pretty=format:'{\"commit\": \"%H\", \"author\": \"%an\", \"date\": \"%ad\", \"message\": \"%s\"}'", "--date=iso"],
            cwd=repo_dir,
            universal_newlines=True
        )

        print(f"\n >>>  \nCommits between {prev_tag} and {tag_name}:\n{commits}")

        # 将每一行的 JSON 字符串转换为字典并收集到一个列表
        commit_list = []
        for line in commits.strip().split("\n"):
            # 去掉多余的单引号并解析 JSON 字符串
            line = line.strip("'")
            commit_dict = json.loads(line)
            commit_list.append(commit_dict)

        for commit in commit_list:
            commit_hash = commit['commit']
            commit['commit_html'] = f"{repo_url}/commit/{commit_hash}"

        print(f"commit_list: {commit_list}")
        # 返回结果
        return jsonify({
            "tag_name": tag_name,
            "previous_tag": prev_tag,
            "commits": commits.strip()
        })

    return jsonify({"message": "Not a tag push event"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
