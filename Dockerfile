# =================================================================
# Dockerfile for Clinician-Friendly WES Pipeline (Thyroid/Parathyroid)
# Based on GATK Best Practices & STAR Protocol
# =================================================================

# 1. 베이스 이미지: GATK가 이미 설치된 공식 이미지를 사용 (가장 안전하고 편함)
FROM broadinstitute/gatk:4.4.0.0

# 메타데이터: 논문에 들어갈 저자 정보
LABEL maintainer="Seon-Hoon Lee Lab"
LABEL description="User-friendly WES pipeline for Thyroid & Parathyroid disorders"
LABEL version="1.0"

# 2. 추가 필수 도구 설치 (BWA, Samtools, Python 라이브러리)
# 리눅스 환경 세팅을 자동으로 수행합니다.
RUN apt-get update && apt-get install -y \
    bwa \
    samtools \
    python3-pip \
    && apt-get clean

# 3. 파이썬 분석 라이브러리 설치 (pandas, openpyxl 등 리포트 생성용)
RUN pip3 install pandas openpyxl

# 4. 분석에 필요한 파일들을 컨테이너 내부로 복사
# (선생님의 파이썬 스크립트와 타겟 유전자 리스트를 넣는 과정)
WORKDIR /pipeline
COPY pipeline_script.py /pipeline/
COPY targets.bed /pipeline/

# 5. 실행 권한 부여
RUN chmod +x /pipeline/pipeline_script.py

# 6. 컨테이너가 시작될 때 실행할 기본 명령어
# 사용자가 별도 명령 없이 실행하면 도움말을 출력하거나 파이프라인을 가동
ENTRYPOINT ["python3", "/pipeline/pipeline_script.py"]