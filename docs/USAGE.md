# Usage and troubleshooting

## Install one LUT on EOS RP

1. Connect the EOS RP by USB.
2. Start the loader.
3. Choose `.cube`, Hald `.tif/.tiff`, or `.pf3`.
4. For `.cube`/Hald input, optionally set the generic LUT adjustments.
5. Generate the working PF3.
6. Select User Def. 1/2/3 and arm the install.
7. In EOS Utility go to **Camera settings → Register Picture Style File**.
8. Select the same slot, load the PF3 shown by the app, and press **OK**.
9. A successful loader-side sequence includes:

```text
Self-test compiler: ... MATCH EXATO
Registo detetado: User Def. N (16752 bytes)
Payload RP 16752 substituído
EOS Utility escreveu 0x01000203: rc=0 patched=True
0x00000115 observado (32 bytes) e deixado INTACTO
```

## Installing another preset

Close EOS Utility completely, reopen it, then repeat the registration. Reusing the same EOS Utility process is currently less reliable and can result in the next registration not being intercepted.

## White / blank camera preview

Do not use the old v2.0 behavior that modified `0x00000115`. Current versions leave it untouched. If a slot was previously written by the affected experimental build, register the style again through the corrected loader.

## Image looks normal / LUT seems absent

Check the generated report/log. If the install remained armed and there was no `registration_seen`, `payload_patched`, and successful `registration_return`, the normal Canon registration was not intercepted. Restart EOS Utility and retry.

## Generic adjustments

The optional adjustment panel is independent of the source LUT. It can bake Highlight, Shadow, Color, Color Chrome-style, and Blue Chrome-style transforms into one final 33³ LUT before PF3 generation.

The Chrome-style controls are experimental generic color-density transforms; they are not claimed to reproduce Fujifilm's proprietary implementation exactly.
