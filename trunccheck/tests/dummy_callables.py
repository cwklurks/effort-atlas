def extract_last(text):
    if "RAISE" in text:
        raise RuntimeError("dummy failure")
    if "Final answer:" in text:
        return text.split("Final answer:", 1)[1].strip().split()[0]
    return ""

def score_equal(extracted, gold):
    return extracted == gold
