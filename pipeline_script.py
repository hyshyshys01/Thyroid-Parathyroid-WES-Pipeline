import os
import subprocess
import pandas as pd

# ==========================================
# 1. 환경 설정 (Configuration)
# ==========================================
# 분석에 필요한 도구들의 경로와 파일명을 설정합니다.
SAMPLE_ID = "Patient_01"
R1_FASTQ = "data/Patient_01_R1.fastq.gz"
R2_FASTQ = "data/Patient_01_R2.fastq.gz"

# Reference Files (hg38 권장)
REF_GENOME = "ref/Homo_sapiens_assembly38.fasta"
DBSNP = "ref/dbsnp_146.hg38.vcf.gz"

# 선생님의 핵심 아이디어: Target Gene List (BED 파일)
# 예: RET, CASR, PAX8 등의 염색체 위치가 적힌 파일
TARGET_BED = "targets.bed" 

# 도구 경로 (Docker를 쓴다면 명령어만 있으면 됨)
BWA = "bwa"
GATK = "gatk"
SAMTOOLS = "samtools"
ANNOVAR = "table_annovar.pl"

# ==========================================
# 2. 실행 함수 정의 (Wrapper Function)
# ==========================================
def run_command(cmd, step_name):
    print(f"\n[INFO] Starting Step: {step_name}")
    print(f"Command: {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
        print(f"[SUCCESS] {step_name} completed.\n")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {step_name} failed.")
        exit(1)

# ==========================================
# 3. 메인 파이프라인 (Main Workflow)
# ==========================================
def main():
    # --- Step 1: Alignment (BWA-MEM) [STAR Protocol Ref] ---
    # FASTQ를 Reference Genome에 매핑하여 SAM 파일을 만듭니다.
    cmd_bwa = f"{BWA} mem -t 8 -R '@RG\\tID:{SAMPLE_ID}\\tSM:{SAMPLE_ID}\\tPL:ILLUMINA' {REF_GENOME} {R1_FASTQ} {R2_FASTQ} > {SAMPLE_ID}.sam"
    run_command(cmd_bwa, "1. BWA Alignment")

    # --- Step 2: Sorting & Indexing (Samtools) ---
    # SAM을 컴퓨터가 읽기 편한 BAM으로 변환하고 정렬합니다.
    cmd_sort = f"{SAMTOOLS} view -bS {SAMPLE_ID}.sam | {SAMTOOLS} sort -o {SAMPLE_ID}.sorted.bam"
    run_command(cmd_sort, "2. BAM Sorting")
    
    run_command(f"{SAMTOOLS} index {SAMPLE_ID}.sorted.bam", "2-1. BAM Indexing")

    # --- Step 3: Mark Duplicates (GATK) ---
    # PCR 과정에서 생긴 중복된 리드(Noise)를 제거합니다.
    cmd_dedup = f"{GATK} MarkDuplicates -I {SAMPLE_ID}.sorted.bam -O {SAMPLE_ID}.dedup.bam -M {SAMPLE_ID}.metrics.txt"
    run_command(cmd_dedup, "3. Mark Duplicates")

    # --- Step 4: Variant Calling (GATK HaplotypeCaller) ---
    # ★ 핵심 포인트: -L 옵션을 사용하여 25개 유전자(TARGET_BED)만 집중 분석합니다.
    # 전체 Exome을 다 부르는 것보다 속도가 훨씬 빠르고 정확합니다.
    cmd_hc = (
        f"{GATK} HaplotypeCaller "
        f"-R {REF_GENOME} "
        f"-I {SAMPLE_ID}.dedup.bam "
        f"-O {SAMPLE_ID}.vcf "
        f"-L {TARGET_BED} "  # <--- 선생님의 Virtual Panel 적용
        f"--interval-padding 100" # 유전자 앞뒤 100bp 여유
    )
    run_command(cmd_hc, "4. Variant Calling (Targeted)")

    # --- Step 5: Annotation (ANNOVAR) ---
    # 발견된 변이에 '이름표(기능, 질병 연관성)'를 붙입니다.
    cmd_anno = (
        f"{ANNOVAR} {SAMPLE_ID}.vcf humandb/ -buildver hg38 "
        f"-out {SAMPLE_ID}.anno -remove -protocol refGene,cytoBand,gnomad211_exome,clinvar_20221231,dbnsfp42a "
        f"-operation g,r,f,f,f -nastring . -vcfinput"
    )
    run_command(cmd_anno, "5. Annotation")

    # --- Step 6: Final Filtering (Python Pandas) ---
    # "Clinician-Friendly" 리포트를 만드는 과정입니다.
    # ANNOVAR 결과(txt)를 읽어서 의사가 보기 편한 엑셀로 저장합니다.
    print("[INFO] Generating Final Clinical Report...")
    
    # 예시: ANNOVAR 결과 읽기
    df = pd.read_csv(f"{SAMPLE_ID}.anno.hg38_multianno.txt", sep="\t")
    
    # 필터링 조건: 
    # 1. Pathogenic 가능성이 높은 것 (SIFT < 0.05 or PolyPhen > 0.9 or ClinVar='Pathogenic')
    # 2. 너무 흔한 변이(Population Frequency > 1%) 제외
    
    relevant_variants = df[
        ((df['SIFT_score'] < 0.05) | (df['Polyphen2_HVAR_score'] > 0.909) | (df['CLNSIG'].str.contains('Pathogenic', na=False))) &
        (df['gnomAD_exome_ALL'] < 0.01)
    ]
    
    # 최종 저장
    output_filename = f"{SAMPLE_ID}_Thyroid_Panel_Report.xlsx"
    relevant_variants.to_excel(output_filename, index=False)
    print(f"[SUCCESS] Report Saved: {output_filename}")

if __name__ == "__main__":
    main()
