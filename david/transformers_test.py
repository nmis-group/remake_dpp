import torch
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument
from transformers import AutoProcessor, AutoModelForVision2Seq
from transformers.image_utils import load_image
from pathlib import Path
from PIL import Image
from torch.profiler import profile, ProfilerActivity, record_function

# torch.backends.cudnn.benchmark = True
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load images
# image = load_image("https://huggingface.co/ibm-granite/granite-docling-258M/resolve/main/assets/new_arxiv.png")
image = load_image("/home/david/projects/doclingtest/output2_001.jpg")
w, h = image.size
new_w = w * 2
new_h = int(h * (new_w / w))
out = image.resize((new_w, new_h), Image.LANCZOS)
image = out

# Initialize processor and model
processor = AutoProcessor.from_pretrained("ibm-granite/granite-docling-258M")
model = AutoModelForVision2Seq.from_pretrained(
    "ibm-granite/granite-docling-258M",
    torch_dtype=torch.bfloat16,
    #_attn_implementation="flash_attention_2" if DEVICE == "cuda" else "sdpa",
    _attn_implementation="sdpa",
).to(DEVICE)
model

print(f"Top-level config.use_cache : {model.config.use_cache}")
print(f"Text-model config.use_cache: {model.model.text_model.config.use_cache}")

# Create input messages
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": "Convert this page to docling."}
        ]
    },
]

# Prepare inputs

prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=prompt, images=[image], return_tensors="pt")
inputs = inputs.to(DEVICE)

# Generate outputs
with profile(activities=[ProfilerActivity.CPU]) as prof:
    with record_function("model_inference"):
        generated_ids = model.generate(**inputs, max_new_tokens=8192, use_cache=True, do_sample=False)
        prompt_length = inputs.input_ids.shape[1]
        trimmed_generated_ids = generated_ids[:, prompt_length:]
        doctags = processor.batch_decode(
            trimmed_generated_ids,
            skip_special_tokens=False,
        )[0].lstrip()
        print(f"DocTags: \n{doctags}\n")
prof.export_chrome_trace("trace2.json")

print(f"DocTags: \n{doctags}\n")


# Populate document
doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
# create a docling document
doc = DoclingDocument.load_from_doctags(doctags_doc, document_name="Document")
print(f"Markdown:\n{doc.export_to_markdown()}\n")

## export as any format.
# Path("out/").mkdir(parents=True, exist_ok=True)
# HTML:
# output_path_html = Path("out/") / "example.html"
# doc.save_as_html(output_path_html)
# Markdown:
# output_path_md = Path("out/") / "example.md"
# doc.save_as_markdown(output_path_md)