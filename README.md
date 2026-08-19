EOS RP Custom LUT / Picture Style Loader — v2.3 Alpha

This release marks the first practical version of the project where arbitrary LUTs can be converted and used as in-camera Picture Styles on the Canon EOS RP.

Canon's newer cameras compile Picture Styles differently from older DSLR models. During testing, I found that the EOS 1300D compilation path preserves the custom dense LUT information, while the EOS RP's normal compilation path produces a different representation that does not preserve the same custom LUT data.

The current loader works around this by compiling the LUT through the legacy Picture Style path, extracting the resulting LUT block, and injecting that block into a valid EOS RP Picture Style payload during the normal EOS Utility registration process.

What works
Import standard .cube 3D LUTs
Import Hald CLUT TIFFs
Load compatible .pf3 files
Convert LUTs into Canon's internal 33×33×33 Picture Style LUT representation
Compile the LUT through Canon's legacy Picture Style compiler
Inject the resulting LUT block into an EOS RP registration payload
Register the final Picture Style through EOS Utility
Custom Picture Style names
Generic LUT adjustments before conversion:
Highlight
Shadow
Color
Color Chrome-style
Blue Chrome-style
Save and load reusable LUT-adjustment presets
Basic workflow
Connect the EOS RP to the computer.
Open the loader.
Select a .cube, Hald TIFF or compatible .pf3.
Optionally apply LUT adjustments.
Generate the Picture Style.
Prepare the installation.
Register the generated PF3 normally through EOS Utility.
The loader detects the registration and replaces the appropriate LUT block before EOS Utility sends it to the camera.

The resulting look can then be selected and used in-camera like a normal Custom Picture Style.

Important

This is currently a loader-assisted solution.

It does not yet generate a completely standalone arbitrary .pf3 that can simply be loaded onto newer Canon cameras without the helper running.

EOS Utility is still used to perform the actual camera registration because the EOS RP requires additional internal state/transaction behaviour that has not yet been reproduced through direct EDSDK calls.

EOS Utility restart

For repeated Picture Style registrations, the most reliable workflow currently is:

Close EOS Utility completely after installing a Picture Style and reopen it before installing the next one.

The loader itself can remain open.

Supported camera
Tested
Canon EOS RP

The legacy compilation process has also been extensively tested against the EOS 1300D, which was used to reverse-engineer the older LUT representation.

Other Canon cameras have not yet been validated. DIGIC 8 or similarly structured cameras may potentially use a related format, but compatibility should not be assumed.

LUT adjustments

The application only exposes adjustments that can actually be represented as RGB → RGB transformations inside a 3D LUT:

Highlight
Shadow
Color
Color Chrome-style
Blue Chrome-style

Camera-side parameters such as ISO, Dynamic Range, White Balance, sharpening and noise reduction are intentionally not included.

Spatial effects such as grain and clarity cannot be represented correctly by a 3D LUT and are also not included.

The Color Chrome-style controls are experimental transforms inspired by color-density behaviour and are not claimed to reproduce Fujifilm's proprietary Color Chrome processing exactly.

Technical progress

A few major findings made this release possible:

Canon Picture Styles can contain dense 33³ RGB LUTs.
The EOS 1300D compiler converts these into a compact legacy LUT representation.
The compiler output was validated against physical camera captures.
The EOS RP uses a 16,752-byte compiled Picture Style payload.
The primary LUT transformation is carried by the first 8192-byte LUT block in the tested EOS RP payload.
Replacing that block with a correctly compiled legacy LUT allows the EOS RP to execute the custom transformation.
Canon property 0x00000115 is treated as binary state/control data and is never modified by the loader.

The compiler self-test included in the loader checks the known Superia reference block before allowing an installation.

Known limitations
Windows only for now.
Canon EOS Utility is required.
EOS RP is currently the only modern camera validated.
The installation still requires manually registering the generated PF3 through EOS Utility.
Direct EDSDK installation is not yet working because the camera rejects the compiled payload outside Canon's internal registration transaction.
Some LUTs may require adjustment because Canon's image-processing pipeline is not identical to the pipeline the LUT was originally designed for.
Very extreme transforms may clip or behave differently from their original implementation.
Experimental software

This project is based on reverse engineering and is still experimental.

Back up anything important and use it at your own risk.

This project is not affiliated with or endorsed by Canon, Fujifilm, Adobe, or any other camera/software manufacturer.

No proprietary Canon DLLs are distributed with the project.

What's next

Current areas of investigation include:

compatibility with other modern Canon bodies;
removing the need for the loader during registration;
reproducing the EOS Utility transaction directly through EDSDK;
improving LUT colour-management and input/output pipeline handling;
additional Picture Style controls;
further analysis of Canon's compact LUT representation.

If you test this on another Canon camera, please open an issue and include the camera model, EOS Utility version, and loader report.
