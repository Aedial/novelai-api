"""
{filename}
==============================================================================

| Example of how to generate an image with inpainting
|
| The resulting image will be placed in a folder named "results"
"""

import asyncio
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ImageModel, ImagePreset


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        model = ImageModel.Anime_v4_Curated
        information_extracted = 1
        reference_strength = 0.6

        # Note: this is not the same as a .naiv4vibe file, it only contains the "encoding" data
        encoded_image_file = d / "encoded_image.b64"
        nai4vibe_file = d / "encodings.naiv4vibe"

        if nai4vibe_file.exists():
            # If you have a .naiv4vibe file, you can extract the encoded image(s) from it
            # Note: a .naiv4vibe file can contain multiple encoded images (all the ones cached by your browser)
            encoded_images = ImagePreset.references_from_nai4vibe(nai4vibe_file, model)

            current_index = 1
            if len(encoded_images) < current_index:
                raise ValueError(f"Expected at least {current_index} encoded image, got {len(encoded_images)}")

            print(f"Using encoded image {current_index}/{len(encoded_images)} from {nai4vibe_file}")
            encoded_image, information_extracted = encoded_images[current_index - 1]

        elif not encoded_image_file.exists():
            # NOTE: this step consumes 2 anlas! You can save the encoded image and reuse it later.
            #       As information extracted is a parameter, you need to encode the image again if you change it.
            image = (d / "image_v4_2.png").read_bytes()

            # FIXME: weirdly, this doesn't seem to work, even though it behaves the same as the web version
            #       ImagePreset.references_from_nai4vibe works fine, tho
            encoded_image = await api.high_level.encode_vibe(image, model, information_extracted)
            encoded_image_file.write_text(encoded_image)
        else:
            encoded_image = encoded_image_file.read_text("utf-8")

        preset = ImagePreset.from_default_config(model)
        preset.reference_image_multiple = [encoded_image]
        preset.reference_strength_multiple = [reference_strength]
        preset.seed = 42

        preset.characters = [
            # prompt, uc, position
            {"prompt": "boy"},  # default position is "C3"
            {"prompt": "girl", "position": "A3"},
        ]

        prompt = "1girl, 1boy"
        async for _, img in api.high_level.generate_image(prompt, model, preset):
            (d / "image_with_vibe_v4.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(main())
