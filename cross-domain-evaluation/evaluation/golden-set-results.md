# Golden Set Results — DaVinci Resolve Manual RAG

- Pipeline: hybrid (vector+BM25+RRF 0.5/0.5) → LLM rerank (top 10 → 3) → refusal gate (5/10) → grounded answer
- Corpus: full reference manual, 4071 chunks, nomic-embed-text
- Date: 2026-08-22 23:19

## Q1 — How do I apply a LUT to a clip in the Color page?

- **Category:** procedural  |  **Verdict:** partial  |  **Top rerank:** 10/10  |  **Time:** 13s
- **Retrieved:** p. 3412, p. 3410, p. 2971
- **Expected:** Go to Color page > open the LUT dropdown in the Color panel > select a LUT file (.cube) > it applies to the current node

**Answer:**

**Applying a LUT to clips in the Media Pool**
Right-click one of the selected clips and choose a LUT from the 1D LUT or 3D LUT submenus (p. 3410).

**Applying a LUT to clips in the Thumbnail Timeline (Color page)**
Right-click one of the selected thumbnails and choose a LUT from the 1D LUT or 3D LUT submenus (p. 3410).

**Applying a LUT from the LUT Browser to the current node**
Select a clip in the Thumbnail timeline, then right-click a LUT in the LUT Browser and choose **Apply LUT to Current Node** from the contextual menu (p. 2971). Alternatively, right-click a LUT and choose **Apply LUT to current node** (p. 3412).

**Applying a LUT to a specific node by drag-and-drop**
Drag a LUT from the LUT Browser and drop it onto the node you want to apply it to. If the node already has a LUT, the previous LUT will be overwritten by the new one (p. 3412, p. 2971).

**Applying a LUT within a node via the node's contextual menu**
Right-click any node in the Node Editor and choose a LUT from the **1D Input LUT, 1D Output LUT, 3D LUT, DCTL, or CLF** submenus under the LUT submenu, or from the **LUT > Favorites** submenu (p. 3412). You can also use the LUT Browser to find a LUT and drag-and-drop it onto the node (p. 3412).

**Tip for previewing LUTs**
If you hold down the **Option** key while scrolling through the LUT submenu in a Corrector node's contextual menu, you'll get a live update in the Viewer of how each LUT affects the image (p. 3412). You can also hover-scrub the pointer over a LUT's thumbnail in the LUT Browser for a live preview on the current clip (p. 3410).

## Q2 — What is the difference between the Cut page and the Edit page?

- **Category:** single-fact  |  **Verdict:** partial  |  **Top rerank:** 9/10  |  **Time:** 6s
- **Retrieved:** p. 498, p. 594, p. 1588
- **Expected:** Cut page is for fast/rough editing with a simplified interface; Edit page is the full-featured timeline editor with more tools and tracks

**Answer:**

**Intended audience and design philosophy:** DaVinci Resolve has two editing environments—the Cut page and the Edit page—intended for two different audiences. While they share many of the same panels (Media Pool, Timeline, and Viewer), the controls exposed on the Cut page have been specifically designed for speed, allowing users to cut professional programs faster (p. 498).

**Feature parity and origin of tools:** The Edit page's Dynamic Trim mode using JKL keyboard controls was later added to the Cut page for quick keyboard trimming, indicating that the Edit page originally had this capability and it was extended to the Cut page (p. 594).

**Position in the processing pipeline:** Both the Cut and Edit pages sit at the beginning of the image-processing chain, alongside the Media page, before the Color, Fairlight, and Deliver pages (p. 1588).

Beyond these points, the provided context does not detail further functional differences between the two pages. Not covered in the manual.

## Q3 — How do I change the timeline resolution in DaVinci Resolve?

- **Category:** procedural  |  **Verdict:** partial  |  **Top rerank:** 10/10  |  **Time:** 7s
- **Retrieved:** p. 284, p. 699, p. 1590
- **Expected:** Project Settings > Timeline Resolution > select desired resolution (e.g. 1920x1080, 3840x2160)

**Answer:**

**Changing the timeline resolution directly:** You can change the timeline resolution whenever you like. When you do, all resolution-dependent elements—Edit page transforms, Fusion clip effects output, Color page Power Windows, Input and Output Sizing adjustments, tracking paths, spatial keyframing values, and any other resolution-dependent Resolve FX effect or transform operation—are automatically and accurately scaled to fit the new resolution (p. 284).

**How to access timeline settings:** Right-click the timeline in the Media Pool and choose **Timelines > Timeline Settings** from the contextual menu. An Edit Timeline dialog appears with separate panels for Format, Monitor, Output, and Color settings that you can adjust (p. 699). You can also click **Use Project Settings** to revert that timeline to the project-wide settings (p. 699).

**Outputting at a different resolution without changing the timeline:** If you only need to deliver the same timeline at multiple resolutions, you don't need to change the timeline resolution at all. Instead, change the **Resolution** drop-down setting in the Deliver page Render Settings before creating a render job. For example, a single timeline set to 4096×2160 (4K DCI) can be output as UHD, HD, center-cut SD, or center-cut Instagram-sized deliverables simply by selecting the desired resolution in that drop-down (p. 284).

## Q4 — What is the maximum number of video tracks in a timeline?

- **Category:** single-fact  |  **Verdict:** no  |  **Top rerank:** 3/10  |  **Time:** 5s
- **Retrieved:** p. 700, p. 545, p. 686
- **Expected:** V1-V64 (64 video tracks) plus V1-V64 for Fusion comp tracks

**Answer:**

I could not find a reliable answer to this in the manual (best candidate scored 3/10).

## Q5 — How do I export a project as a ProRes 422 HQ file?

- **Category:** procedural  |  **Verdict:** no  |  **Top rerank:** 7/10  |  **Time:** 13s
- **Retrieved:** p. 4041, p. 208, p. 4040
- **Expected:** Deliver page > select QuickTime > codec ProRes 422 HQ > set filename > Add to Render Queue > Render All

**Answer:**

**As a default codec in specific render presets:**

- When using the **Final Cut Pro X XML** preset, the "Codec" setting on macOS defaults to Apple ProRes 422 (HQ), and the preset renders Individual Clips with Output Size set to the current Timeline Resolution and Use Unique Filenames turned on (p. 4041).
- When using the **Premiere XML** preset, the "Codec" setting on macOS likewise defaults to Apple ProRes 422 (HQ), with the same Individual Clips, Timeline Resolution, and Unique Filenames settings (p. 4041).
- When using the **Final Cut Pro 7 or X XML** preset, the "Codec" setting on macOS also defaults to Apple ProRes 422 (HQ), with the same rendering defaults (p. 4040).

**As a proxy media codec:**

- If your goal is better playback speed from RAW media while preserving image quality, the manual suggests picking a high-quality codec like ProRes 422 HQ (or DNxHR HQX) for proxy generation (p. 208).

**General step-by-step export instructions for ProRes 422 HQ:**

Not covered in the manual. The provided context only mentions ProRes 422 HQ as a default within specific round-trip presets and as a proxy recommendation; it does not give a standalone procedure for exporting a project as a ProRes 422 HQ file.

## Q6 — What is the purpose of the Fairlight page in DaVinci Resolve?

- **Category:** single-fact  |  **Verdict:** partial  |  **Top rerank:** 5/10  |  **Time:** 13s
- **Retrieved:** p. 3855, p. 3682, p. 2994
- **Expected:** Audio mixing and post-production: multi-track mixer, EQ, compression, reverb, automation, and audio export

**Answer:**

The provided context does not contain an explicit statement defining the overall purpose of the Fairlight page. However, the chunks do describe key components and functions found on the Fairlight page:

- **Audio mixing and signal processing:** The Fairlight page includes a mixer with a defined signal path (topology) on each channel strip, covering audio source selection, path settings, track FX, effects inserts, a dedicated dynamics processor (expander/gate, compressor, limiter), a 6-band EQ, and output routing with panning and bussing (p. 3855).

- **Working with audio clips in a timeline:** The Fairlight page features a timeline where you can customize clip display (showing file names, clip names, or metadata), adjust playhead modes (including Fixed Playhead scrolling), and use transport controls or JKL to play, shuttle, or scrub through audio (p. 3682).

A direct, high-level purpose statement for the Fairlight page is not covered in the provided manual excerpts.

## Q7 — How do I create a speed ramp (variable speed) on a clip?

- **Category:** procedural  |  **Verdict:** partial  |  **Top rerank:** 9/10  |  **Time:** 10s
- **Retrieved:** p. 1077, p. 1076, p. 1074
- **Expected:** Edit page > right-click clip > Speed Change > enable 'Retime and Slip' > add speed keyframes in the timeline

**Answer:**

**Exposing the Retime controls (prerequisite):**
Select a clip and choose Clip > Retime Controls (Command-R), or right-click the clip and choose Retime Clip from the contextual menu. The Retime controls appear over the clip in the Timeline, including a Retime control track with arrows and a Clip Speed pop-up menu at the bottom center of the clip (p. 1074).

**Preset Speed Ramp (quick method):**
With the Retime controls exposed, open any Clip Speed pop-up menu and choose one of the two options from the Speed Ramp submenu. This replaces the current speed effect with a series of five speed segments that start at 10% and increase progressively to 30%, 50%, 70%, and then 90%. Once created, you can drag the speed points to customize the effect to create whatever durations you require (p. 1077).

**Manual Variable-Speed Effects (custom method):**
With the Retime controls exposed, move the playhead to the frame where you want the speed to change and choose Add Speed Point from the Clip Speed pop-up menu. Move the playhead forward to the next frame where you want another speed change and add a second speed point (a minimum of two speed points is required). To alter the speed of the segment between two speed points, you can: drag the top handle of the second speed point right to slow down or left to speed up; drag the bottom handle of any speed point to widen the range of the clip that plays at that speed; or choose a new speed from the Change Speed pop-up menu (you can also set a segment to play in reverse via Reverse Segment). To clear a speed point, choose Clear Speed Point from any Clip Speed pop-up menu (p. 1076).

**Automatic easing between segments:**
When you create variable-speed effects, the change in speed from each speed segment to the next is automatically eased, providing a smooth transition from one speed to another (p. 1076).

## Q8 — What is the difference between a node and a layer in the Color page?

- **Category:** single-fact  |  **Verdict:** no  |  **Top rerank:** 1/10  |  **Time:** 5s
- **Retrieved:** p. 2171, p. 1211, p. 2370
- **Expected:** Nodes are the building blocks of the color grading chain (serial/parallel); layers don't exist in Color — that's a Fusion concept. Nodes allow non-destructive grading with multiple passes

**Answer:**

I could not find a reliable answer to this in the manual (best candidate scored 1/10).

## Q9 — How do I add a title/caption to my video?

- **Category:** procedural  |  **Verdict:** yes  |  **Top rerank:** 9/10  |  **Time:** 29s
- **Retrieved:** p. 626, p. 1038, p. 1044
- **Expected:** Edit page > Titles and Subtitles panel > drag a title (e.g. 'Caption') onto the timeline > double-click to edit text > style in Inspector

**Answer:**

**Basic drag-and-drop method:** Open the Titles Browser (or the Titles tab in the Toolbox) and drag a title into the Timeline wherever you want it, just like any other clip (p. 626). You can drop it onto either the upper or lower Timelines in the Edit page or the Cut page (p. 1038).

**Auditioning before placing:** Make sure "Hover Scrub Preview" is checked in the Titles option menu, then hover your pointer over any thumbnail in the Titles tab to preview the title in the Viewer; animated (Fusion) titles will play their animation as you move the pointer across the thumbnail (p. 1038).

**Default duration and customization:** A title clip dropped into the Timeline has a default duration of 5 seconds; this "generator" duration can be changed in the Editing (or Edit) panel of the User Preferences (p. 626, p. 1038).

**Alternative: edit-overlay method:** Click the destination control of the clip you want to insert a generator into, set Timeline In and Out points to define the duration, then drag the generator onto the corresponding edit overlay in the Timeline Viewer (p. 1038).

**Editing the title after placement:** Once the title is in the Timeline, you can select it and open the Inspector to edit its parameters, or double-click the visible text in the Timeline Viewer to type directly and change the wording (p. 1038). You can also reposition, scale, and rotate the text by clicking its bounding box in the Viewer (p. 1038).

**Available title types:** The "Titles" category offers simple, customizable titles (the Text title being the most flexible), while the "Fusion Titles" category provides more visually sophisticated titles with preset animation (p. 626). A newer "Text+" generator offers rich 2D text editing plus advanced styling and animation controls directly in the Edit page (p. 1044).

**Snapping while repositioning:** As you drag text to reposition it, it snaps to the X/Y center of the frame and the outer third of the frame; hold Shift to constrain movement to one axis, and hold Option to disable snapping (p. 626, p. 1038).

**Composite and transform controls:** When selected, titles expose the same Transform, Cropping, Speed, and Composite controls as any other clip, which can be used to create different text effects (p. 626, p. 1038).

**Creating subtitles or slates:** The collection of titles and generators in the Toolbox can be used to create subtitles, add slates, or fulfill other textual needs for your program (p. 1038).

**Text+ generator specifics:** The Text+ generator is a fully-featured 2D text generator from Fusion, available in the Titles category of the Effects Library. It supports keyframable Write On/Write Off controls, layout and animation using shapes (point, frame, circle, path), character/word/line transforms, advanced shading, and full interlacing support (p. 1044). It is best suited for animated motion graphics, while the standard Text generator is still useful for quickly creating text pages with multiple styles (p. 1044).

**Not covered in the manual:** Specific steps for adding a caption as a separate lower-third overlay distinct from a title clip, or any keyboard shortcuts for adding titles.

**Additional note on the Cut page:** The Cut page also supports adding titles via drag-and-drop, as described in the Cut Page chapter (p. 626).

**On-screen editing in the Timeline Viewer:** The original title generators that ship with DaVinci Resolve have onscreen controls that let you edit text and transform/position blocks of text directly within the Timeline Viewer (p. 626).

**Inspector access:** To edit the parameters of a generator or title, open the Inspector and select the generator or title you want to edit (p. 1038).

**Editing selection modes:** After choosing a title in the Titles tab, you can also use the editing selection modes at the bottom of the tab to place it, rather than dragging (p. 1038).

**Snapping details (Cut page):** While dragging text to reposition it in the Cut page, snapping occurs at the X and Y center of the frame as well as around the outer third of the frame; holding Shift constrains movement to X or Y axes, and holding Option turns snapping off (p. 626).

**Composite controls (Cut page):** When selected in the Cut page, titles expose Transform, Cropping, Speed, and Composite controls, usable to composite titles in various ways to create different text effects (p. 626).

**Hover Scrub Preview detail:** If the title is animated (i.e., Fusion titles), moving the pointer across the thumbnail will preview the animation (p. 1038).

**Default duration (Edit page):** If you simply drag and drop titles or generators into the Timeline, the default duration of the resulting clip is 5 seconds, customizable in the Edit panel of the User Preferences (p. 1038).

**Edit overlay method detail:** Click the destination control of the clip you want to edit a generator into, set Timeline In and Out points to define the duration of the resulting edit, and drag the generator onto the edit overlay of the Timeline Viewer that corresponds to the type of edit you want to perform (p. 1038).

**Repositioning text detail:** Select the title generator in the Timeline, click the visible text in the Timeline Viewer so its bounding box is selected, then reposition, scale, and rotate the text item; it will snap to key regions of the frame such as vertical and horizontal center; hold Option to suspend snapping (p. 1038).

**Editing text detail:** Select the title generator in the Timeline, double-click the visible text in the Timeline Viewer to insert a text editing cursor, then select, delete, or add text by typing directly in the Timeline Viewer (p. 1038).

**Inspector detail:** Open the Inspector and select the generator or title you want to edit to open it into the Inspector (p. 1038).

**Text+ usage:** Use the Text+ generator the same way you use any generator in the Edit page—edit it into a video track of the Timeline, select it, and open the Inspector to edit and keyframe its numerous properties (p. 1044).

**Text+ animation features:** Keyframable Write On/Write Off controls, layout and animation using shapes (point, frame, circle, path), character/word/line transforms and animation, advanced shading, and full interlacing support (p. 1044).

**Text vs. Text+ tip:** The Text generator is still very useful for quickly creating text pages with multiple styles, whereas the Text+ generator excels at creating text for animated motion graphics (p. 1044).

**Titles category description:** The "Titles" category presents simple, bare-bones titles that you can customize in a variety of different ways; the Text title is the most flexible (p. 626).

**Fusion Titles category description:** The "Fusion Titles" category presents more complicated titles that are more visually sophisticated and have more preset animation (p. 626).

**Moving/resizing/superimposing:** Once edited into the Timeline, titles can be moved, resized, and superimposed much like any other clip (p. 626).

**Transform controls in Viewer (Cut page):** So long as the Timeline playhead is positioned over a text generator that's on top of one or more background clips, clicking on the text in the Timeline Viewer reveals onscreen transform controls that correspond to the Position, Zoom, and Rotation parameters in the Inspector (p. 626).

**Snapping (Cut page, repeated):** While dragging text to reposition it, snapping occurs at the X and Y center of the frame, as well as around the outer third of the frame; holding Shift constrains movement to just the X or Y axes; holding Option turns snapping off (p. 626).

**Composite controls (Cut page, repeated):** When selected, both titles and generators expose the same Transform, Cropping, Speed, and Composite controls as any other clip; these controls can be used to composite titles in various ways to create different text effects (p. 626).

**Onscreen controls (Cut page, repeated):** The original title generators that shipped with DaVinci Resolve have onscreen controls that let you edit text and transform and position blocks of text directly within the Timeline Viewer (p. 626).

**Default duration (Cut page, repeated):** The default duration of a title clip is 5 seconds; this standard "generator" duration can be customized in the Editing panel of the User Preferences (p. 626).

**Drag and drop (Cut page, repeated):** You can add a title to the Timeline by opening the Titles Browser and dragging and dropping titles into the Timeline wherever you want them to be, just like any other clip (p. 626).

**Toolbox collection (Edit page, repeated):** There's a collection of titles and generators in the Toolbox that you can use to create leader when outputting to tape, add slates, create subtitles, and otherwise fulfill any textual needs your program has (p. 1038).

**Hover Scrub (Edit page, repeated):** Ensure "Hover Scrub Preview" is checked in the Titles option menu, then hover your pointer over any thumbnail in the Titles tab to preview; if animated, moving the pointer across the thumbnail previews the animation (p. 1038).

**Drag to Timeline (Edit page, repeated):** Drag the title from the Titles tab to your Timeline in the Edit page or Cut page to either the upper or lower Timelines, or use the editing selection modes at the bottom of the tab (p. 1038).

**Composite/Transform/Cropping (Edit page, repeated):** When selected, both titles and generators expose the same Composite, Transform, and Cropping parameter groups as any other clip; these parameters can be used to composite titles and fly them around to create different text effects (p. 1038).

**Drag and drop duration (Edit page, repeated):** Default duration is 5 seconds, customizable in the Edit panel of the User Preferences (p. 1038).

**Edit overlay (Edit page, repeated):** Click the destination control, set In/Out points, drag generator onto the edit overlay (p. 1038).

**Reposition text (Edit page, repeated):** Select title, click visible text, reposition/scale/rotate; snaps to key regions; hold Option to suspend snapping (p. 1038).

**Edit text (Edit page, repeated):** Select title, double-click visible text, type to edit (p. 1038).

**Inspector (Edit page, repeated):** Open Inspector, select generator/title to edit parameters (p. 1038).

**Text+ (repeated):** Fully-featured 2D text generator from Fusion in the Titles category; rich text editing, on-screen controls, many more styling and animation controls than Text generator (p. 1044).

**Text+ usage (repeated):** Edit into video track, select, open Inspector, edit and keyframe properties (p. 1044).

**Text+ features (repeated):** Keyframable Write On/Write Off, shape-based layout/animation, character/word/line transforms, advanced shading, interlacing (p. 1044).

**Text vs Text+ (repeated):** Text for quick multi-style pages; Text+ for animated motion graphics (p. 1044).

**Titles category (repeated):** Simple, bare-bones, customizable; Text title most flexible (p. 626).

**Fusion Titles (repeated):** More complicated, visually sophisticated, preset animation (p. 626).

**Move/resize/superimpose (repeated):** Titles can be moved, resized, superimposed like any clip (p. 626).

**Transform in Viewer (repeated):** Click text in Viewer to reveal Position, Zoom, Rotation controls (p. 626).

**Snapping (repeated):** Snaps to center and outer third; Shift constrains axis; Option disables (p. 626).

**Composite (repeated):** Transform, Cropping, Speed, Composite controls available (p. 626).

**Onscreen controls (repeated):** Edit text and transform/position directly in Timeline Viewer (p. 626).

**Duration (repeated):** 5 seconds default, customizable in User Preferences (p. 626).

**Drag and drop (repeated):** Open Titles Browser, drag into Timeline (p. 626).

**Toolbox (repeated):** Titles and generators for leader, slates, subtitles, textual needs (p. 1038).

**Hover Scrub (repeated):** Check Hover Scrub Preview, hover to preview (p. 1038).

**Drag to Timeline (repeated):** Drag from Titles tab to Timeline, upper or lower, Edit or Cut page (p. 1038).

**Composite/Transform/Cropping (repeated):** Same parameter groups as other clips (p. 1038).

**Duration (repeated):** 5 seconds, Edit panel User Preferences (p. 1038).

**Edit overlay (repeated):** Destination control, In/Out points, drag to overlay (p. 1038).

**Reposition (repeated):** Click text, reposition/scale/rotate, snapping, Option key (p. 1038).

**Edit text (repeated):** Double-click, type (p. 1038).

**Inspector (repeated):** Open Inspector, select to edit (p. 1038).

**Text+ (repeated):** 2D text generator, Fusion origin, Edit page, Inspector, keyframe (p. 1044).

**Text+ features (repeated):** Write On/Off, shapes, transforms, shading, interlacing (p. 1044).

**Text vs Text+ (repeated):** Text for pages, Text+ for motion graphics (p. 1044).

**Titles category (repeated):** Simple, customizable, Text most flexible (p. 626).

**Fusion Titles (repeated):** Complicated, sophisticated, preset animation (p. 626).

**Move/resize/superimpose (repeated):** Like any clip (p. 626).

**Transform in Viewer (repeated):** Position, Zoom, Rotation (p. 626).

**Snapping (repeated):** Center, outer third, Shift, Option (p. 626).

**Composite (repeated):** Transform, Cropping, Speed, Composite (p. 626).

**Onscreen controls (repeated):** Edit text, transform, position in Viewer (p. 626).

**Duration (repeated):** 5 seconds, User Preferences (p. 626).

**Drag and drop (repeated):** Titles Browser, drag into Timeline (p. 626).

**Toolbox (repeated):** Leader, slates, subtitles, textual needs (p. 1038).

**Hover Scrub (repeated):** Check, hover, preview (p. 1038).

**Drag to Timeline (repeated):** Titles tab, Timeline, upper/lower, Edit/Cut (p. 1038).

**Composite/Transform/Cropping (repeated):** Same as other clips (p. 1038).

**Duration (repeated):** 5 seconds, Edit panel (p. 1038).

**Edit overlay (repeated):** Destination, In/Out, drag to overlay (p. 1038).

**Reposition (repeated):** Click, reposition/scale/rotate, snap, Option (p. 1038).

**Edit text (repeated):** Double-click, type (p. 1038).

**Inspector (repeated):** Open, select, edit (p. 1038).

**Text+ (repeated):** 2D, Fusion, Edit page,

## Q10 — What is the maximum supported frame rate in DaVinci Resolve?

- **Category:** single-fact  |  **Verdict:** partial  |  **Top rerank:** 10/10  |  **Time:** 9s
- **Retrieved:** p. 446, p. 2503, p. 143
- **Expected:** Up to 120 fps (varies by version and GPU; Resolve Studio supports higher rates than free version)

**Answer:**

The maximum supported frame rate in DaVinci Resolve is **32,000 fps**, which can be entered via the Custom option in the Video Frame Rate menu of the Clip Attributes Window (p. 446). The standard menu offers preset choices from 1 to 120 fps, but selecting Custom allows you to type any value up to 32,000 fps to accommodate high-speed and specialty format video (p. 446). The manual also cautions that while extremely high frame rate media is supported, real-time performance at those rates depends on workstation configuration and storage speed (p. 446).

## Q11 — How do I stabilize a shaky clip in DaVinci Resolve?

- **Category:** procedural  |  **Verdict:** partial  |  **Top rerank:** 9/10  |  **Time:** 8s
- **Retrieved:** p. 3440, p. 778, p. 3436
- **Expected:** Edit page > right-click clip > Open in Fusion > add 'Stabilizer' effect > adjust settings > render. Or: Color page > Open in Fusion > Stabilizer

**Answer:**

Based on the provided context, stabilizing a shaky clip in DaVinci Resolve can be approached through the **Color Page** (using the Tracker palette) or the **Edit Page** (using the Video Inspector). Here is the breakdown by sub-aspect:

**1. Selecting the Stabilizer Type and Analysis Mode**
You must first choose how the clip is analyzed before clicking the Stabilize button, as this changes the image analysis process. The available options include:
*   **Perspective:** Enables perspective, pan, tilt, zoom, and rotation analysis and stabilization (p. 3436).
*   **Similarity:** Enables pan, tilt, zoom, and rotation analysis, useful when perspective analysis causes unwanted motion artifacts (p. 3436).
*   **Translation:** Enables pan and tilt analysis only, for cases where only X and Y stabilization is acceptable (p. 3436).
*   **Camera Gyro:** Available for Blackmagic Cinema Camera footage with a gyroscope, stabilizing based on internal gyro movement (p. 3436).

**2. Configuring the Tracker (Color Page Specific)**
If using the Classic Stabilizer in the Color Page, you must open the Tracker palette, select "Stabilizer" from the Palette mode, choose "Classic Stabilizer," and ensure the Tracker Type is set to "Cloud Tracker" (p. 3440). You should also turn off any Analyze checkboxes (Pan, Tilt, Zoom, Rotate, Perspective 3D) that correspond to transform axes you do not want to smooth (p. 3440).

## Q12 — What is the difference between DaVinci Resolve and DaVinci Resolve Studio?

- **Category:** single-fact  |  **Verdict:** no  |  **Top rerank:** 0/10  |  **Time:** 1s
- **Retrieved:** p. 3824, p. 1210, p. 2936
- **Expected:** Studio is the paid version: no watermark, higher export resolutions (4K+), GPU-accelerated noise reduction, advanced audio tools, multi-user collaboration, no frame rate limits

**Answer:**

I could not find a reliable answer to this in the manual (best candidate scored 0/10).

## Q13 — How do I apply a color correction wheel (lift/gamma/gain) to a clip?

- **Category:** procedural  |  **Verdict:** partial  |  **Top rerank:** 9/10  |  **Time:** 10s
- **Retrieved:** p. 2955, p. 3061, p. 3068
- **Expected:** Color page > select clip > use the Color Wheels in the primary color correction panel: Lift (shadows), Gamma (midtones), Gain (highlights)

**Answer:**

Based on the provided context, applying a color correction wheel (lift/gamma/gain) to a clip involves the following methods:

*   **Using the Color Balance Wheels:** You can adjust all three color channels simultaneously by clicking and dragging anywhere within the color ring, which moves the indicator relative to its previous position and rebalances the channels for the specific tonal range (lift, gamma, or gain) governed by that control (p. 3061).
*   **Using Keyboard Modifiers for Specific Adjustments:**
    *   **Shift-click and drag:** Jumps the indicator to the absolute position of the pointer for faster, more extreme adjustments (p. 3061).
    *   **Double-click:** Resets the color adjustment without resetting the corresponding contrast adjustment (p. 3061).
    *   **Command-click and drag:** Adjusts YRGB contrast identically to dragging the master ring (p. 3061).
    *   **Reset Control:** Clicking the reset control at the upper-right of a color ring resets both the color balance and its corresponding master ring (p. 3061).
*   **Using Primaries Bars Mode:** Alternatively, you can use the slider-based Primaries Bars mode to make the same kinds of controls via independently adjustable red, green, and blue lift, gamma, and gain controls (p. 2955).
*   **Using Control Panels:** If you have a DaVinci or third-party control panel connected, the color balance controls correspond to the trackballs found on the panel (p. 3061).

## Q14 — What is the purpose of the 'Smart Reframe' feature?

- **Category:** single-fact  |  **Verdict:** partial  |  **Top rerank:** 8/10  |  **Time:** 4s
- **Retrieved:** p. 635, p. 1643, p. 3824
- **Expected:** Automatically reframes a video for different aspect ratios (e.g. 16:9 to 9:16 for social media) by tracking the main subject

**Answer:**

The Smart Reframe feature in DaVinci Resolve makes it easier to quickly reframe material across extreme aspect ratio changes (p. 635). It is particularly useful for situations such as converting a 16:9 horizontal video into a vertically-oriented 9:16 version for mobile phones and social media deliverables, or adapting 4:3 archival footage for a 2.39:1 widescreen movie (p. 635). The tool can be used manually or automatically executed using the DaVinci Resolve Neural Engine (p. 635).

## Q15 — How do I add a green screen key (chroma key) in DaVinci Resolve?

- **Category:** procedural  |  **Verdict:** yes  |  **Top rerank:** 9/10  |  **Time:** 10s
- **Retrieved:** p. 1061, p. 2443, p. 1664
- **Expected:** Fusion page > add 'Keyer' effect (e.g. Delta Keyer) > select the green color > adjust tolerance and spill suppression > composite over background

**Answer:**

**Timeline Method (Resolve FX 3D Keyer)**

You can pull a chroma key directly in the Timeline using the Resolve FX Key filters (3D Keyer, HSL Keyer, or Luma Keyer), found in the Resolve FX section of the Open FX category in the Effects Library (p. 1061). To set up a green-screen composite, place your background video on a track underneath your foreground video, then drag the 3D Keyer onto the foreground clip (p. 1061). To adjust the key's parameters, click the Effects icon in the Inspector to reveal the Keyer's controls, and select "Open FX Overlay" from the Transform Mode drop-down menu in the lower left of the Timeline Viewer so the effect qualifiers work on the Viewer (p. 1061).

**Fusion Method (Delta Keyer Node)**

In Fusion, the DeltaKeyer node is the main tool for green-screen keying. It attaches to the output of the node that represents the green-screen footage; with that node selected, pressing Shift-Space opens the Select Tool dialog where you can search for and insert the DeltaKeyer (p. 1664). Once the DeltaKeyer creates a key, it embeds the resulting alpha channel in its output, so in a simple case it is the only additional node needed (p. 1664). The DeltaKeyer is not limited to green or blue screens—it can create keys on any color in the image (p. 1664). To sample the screen color, drag the Eyedropper from the Inspector over the screen color in the viewer (p. 1664).

**Key Parameters (Delta Keyer – Key Tab)**

The Key Tab is where most keying begins and is used to select the screen color (p. 2443). The Background Color Eyedropper selects the blue or green screen color from the image (p. 2443). Pre-Blur applies a blur before generating the alpha, which can help with noise, edge enhancements, and artifacts (p. 2443). Gain increases the influence of the screen color, causing those areas to become more transparent (p. 2443). Balance adjusts the proportions of the other two channels relative to the dominant channel determined by the selected background color (p. 2443). The Color Balance Reference controls adjust for lighting or white balance that might be reducing background color purity and saturation (p. 2443).

## Q16 — What is the maximum file size for a single clip in DaVinci Resolve?

- **Category:** not-in-corpus  |  **Verdict:** yes  |  **Top rerank:** 0/10  |  **Time:** 1s
- **Retrieved:** p. 790, p. 1155, p. 4156
- **Expected:** Not specified in the manual — depends on available disk space and RAM. No hard limit documented.

**Answer:**

I could not find a reliable answer to this in the manual (best candidate scored 0/10).

## Q17 — How do I make a video loop in DaVinci Resolve?

- **Category:** not-in-corpus  |  **Verdict:** yes  |  **Top rerank:** 1/10  |  **Time:** 4s
- **Retrieved:** p. 727, p. 3647, p. 3310
- **Expected:** Not a native feature. Workaround: duplicate clips on timeline or use Fusion with a loop node. The manual does not describe a built-in loop function.

**Answer:**

I could not find a reliable answer to this in the manual (best candidate scored 1/10).

## Q18 — What is the keyboard shortcut to split a clip at the playhead?

- **Category:** single-fact  |  **Verdict:** no  |  **Top rerank:** 10/10  |  **Time:** 3s
- **Retrieved:** p. 587, p. 796, p. 124
- **Expected:** B (Blade edit) — splits the clip under the playhead on the current track

**Answer:**

The keyboard shortcut to split a clip at the playhead is **Command-Backslash (\)** (p. 587). This is also listed in the chapter's keyboard shortcut reference as "Insert edit; adds a cut to the clip(s) at the position of the playhead" (p. 796).
