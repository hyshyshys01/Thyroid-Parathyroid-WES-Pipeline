import requests
import csv

# =========================================================
# 1. 선생님의 Target Gene List (Thyroid & Parathyroid)
# =========================================================
# Table 1-gene list.xlsx 내용을 바탕으로 작성했습니다.
# 필요시 리스트에 유전자 심볼을 더 추가하거나 빼시면 됩니다.
GENE_LIST = [
    "RET", "MEN1", "CASR", "CDC73", "GCM2", "GNA11", "AP2S1", "PTH", "AIRE", # Parathyroid / MEN
    "PAX8", "TSHR", "NKX2-1", "TG", "TPO", "SLC26A4", "DUOX2", "DUOXA2",    # Thyroid Dysgenesis/Dyshormonogenesis
    "IYD", "SLC5A5", "THRA", "THRB", "SECISBP2", "FOXE1", "HHEX"            # Additional relevant genes
]

# =========================================================
# 2. 좌표 가져오기 함수 (MyGene.info API 사용)
# =========================================================
def fetch_coordinates(genes, genome_build='hg38'):
    print(f"[INFO] Fetching {genome_build} coordinates for {len(genes)} genes...")
    
    url = "https://mygene.info/v3/query"
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    params = {
        'q': ",".join(genes),
        'scopes': 'symbol',
        'fields': 'genomic_pos,symbol',
        'species': 'human'
    }
    
    response = requests.post(url, data=params, headers=headers)
    data = response.json()
    
    bed_lines = []
    
    print(f"{'Gene':<10} {'Chr':<6} {'Start':<12} {'End':<12}")
    print("-" * 40)
    
    for item in data:
        # 데이터가 정상적으로 반환되었는지 확인
        if 'genomic_pos' in item:
            # genomic_pos가 리스트인 경우(여러 위치)와 딕셔너리인 경우 처리
            g_pos = item['genomic_pos']
            if isinstance(g_pos, list):
                # 리스트라면 hg38과 일치하는 것 찾기 (보통 첫번째 것이 대표적)
                target_pos = g_pos[0] 
            else:
                target_pos = g_pos
            
            # hg38 좌표 추출
            chrom = target_pos.get('chr')
            if chrom:
                # BED 파일 포맷: chrX  start  end  GeneName
                # (BED는 0-based start이므로 start에 -1을 하는 것이 정석이나, GATK는 유연함)
                line = f"chr{chrom}\t{target_pos['start']}\t{target_pos['end']}\t{item['symbol']}"
                bed_lines.append(line)
                print(f"{item['symbol']:<10} chr{chrom:<6} {target_pos['start']:<12} {target_pos['end']:<12}")
        else:
            print(f"[WARNING] Could not find coordinates for: {item.get('query')}")

    return bed_lines

# =========================================================
# 3. 파일 저장
# =========================================================
def save_bed_file(lines, filename="targets.bed"):
    with open(filename, "w") as f:
        # GATK 분석을 위해 헤더 없이 바로 데이터 입력
        for line in lines:
            f.write(line + "\n")
    print(f"\n[SUCCESS] '{filename}' has been created with {len(lines)} genes.")

# 실행
if __name__ == "__main__":
    bed_data = fetch_coordinates(GENE_LIST)
    save_bed_file(bed_data)