"""동기화 단계를 CI와 같은 순서로 한 번에 돌린다.

생성기들은 목차·색·파비콘·메타를 완성된 형태로 찍지 않는다. 그 마무리를
sync_nav → sync_theme → sync_icons → sync_meta 네 단계가 맡는다. 그래서
생성기만 돌리고 커밋하면 색이 하드코딩으로 돌아가거나 파비콘이 빠진 채로
올라간다. 오늘 하루에만 네 번 그랬다.

손으로 올릴 때는 이 스크립트 하나만 돌리면 된다.

    python3 scripts/sync_all.py

--check 를 붙이면 마무리까지 끝난 상태인지 확인만 한다. 남은 게 있으면
무엇이 남았는지 적고 1로 끝난다.

    python3 scripts/sync_all.py --check
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# CI 의 update-events.yml 과 같은 순서다. 순서가 뜻이 있다 — 목차를 먼저
# 맞춰야 새로 생긴 링크까지 색이 입혀지고, 파비콘과 메타는 그다음이다.
STEPS = ["sync_nav", "sync_theme", "sync_icons", "sync_meta", "sync_h1_emoji", "sync_sitemap"]

# 스스로 "할 일이 남았다"를 알려 줄 수 있는 단계. 나머지는 돌린 뒤
# 파일이 바뀌었는지로 판단한다.
HAS_CHECK = {"sync_theme", "sync_meta"}


def run(name: str, check: bool) -> tuple[int, str]:
    cmd = [sys.executable, str(HERE / f"{name}.py")]
    if check and name in HAS_CHECK:
        cmd.append("--check")
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def git_dirty() -> list[str]:
    p = subprocess.run(["git", "status", "--porcelain"],
                       cwd=HERE.parent, capture_output=True, text=True)
    if p.returncode != 0:
        return []
    return [l[3:] for l in p.stdout.splitlines() if l.strip()]


def main() -> int:
    check = "--check" in sys.argv
    before = set(git_dirty())
    failed = []

    for name in STEPS:
        code, out = run(name, check)
        for line in out.splitlines():
            if line.strip():
                print("  " + line)
        if code != 0:
            failed.append(name)

    after = set(git_dirty())
    new = sorted(after - before)

    if check:
        # --check 를 모르는 단계는 파일을 건드렸는지로 본다.
        if failed or new:
            print("\n마무리가 덜 됐다.")
            if failed:
                print("  남은 단계: " + ", ".join(failed))
            if new:
                print("  이 단계들이 고친 파일 %d개:" % len(new))
                for f in new[:12]:
                    print("    " + f)
                if len(new) > 12:
                    print("    … 외 %d개" % (len(new) - 12))
            print("\n커밋하기 전에 'python3 scripts/sync_all.py' 를 돌려라.")
            return 1
        print("\n마무리 상태 좋다 — 올려도 된다.")
        return 0

    if new:
        print("\n%d개 파일을 마무리했다. 이 파일들도 같이 올려야 한다:" % len(new))
        for f in new[:12]:
            print("  " + f)
        if len(new) > 12:
            print("  … 외 %d개" % (len(new) - 12))
    else:
        print("\n고칠 게 없었다.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
