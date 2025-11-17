from transformers import AutoProcessor, AutoModelForVision2Seq
import torch

model_name = "/home/yc-user/EGOR_DONT_ENTER/WINK_hacaton/parsing/src/web/models/NuExtract-2.0-8B"
processor = AutoProcessor.from_pretrained(model_name,
                                        trust_remote_code=True,
                                        padding_side='left',
                                        use_fast=True,
                                        # cache_dir=self.local_dir
                                        )
model = AutoModelForVision2Seq.from_pretrained(model_name,
                                            trust_remote_code=True,
                                            #    torch_dtype=torch.bfloat16,
                                            dtype=torch.bfloat16,
                                            #    attn_implementation="flash_attention_2",
                                            # cache_dir=self.local_dir
                                            )