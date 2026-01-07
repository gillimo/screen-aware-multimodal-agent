//! Fast pixel-based detection for Quest Helper arrows and highlights

use rayon::prelude::*;

/// Find yellow Quest Helper arrow
/// Returns (x, y, confidence) if found
pub fn find_yellow_arrow(img_data: &[u8], width: u32, height: u32) -> Option<(i32, i32, f32)> {
    // Yellow arrow: R > 200, G > 200, B < 80
    // Image data is RGBA, 4 bytes per pixel

    let pixels_per_row = width as usize;
    let total_pixels = (width * height) as usize;

    if img_data.len() < total_pixels * 4 {
        return None;
    }

    // Collect yellow pixel coordinates
    let yellow_pixels: Vec<(usize, usize)> = (0..total_pixels)
        .into_par_iter()
        .filter_map(|i| {
            let offset = i * 4;
            let r = img_data[offset];
            let g = img_data[offset + 1];
            let b = img_data[offset + 2];

            // Bright yellow detection
            if r > 200 && g > 200 && b < 80 {
                let x = i % pixels_per_row;
                let y = i / pixels_per_row;
                Some((x, y))
            } else {
                None
            }
        })
        .collect();

    if yellow_pixels.len() < 10 {
        return None;
    }

    // Calculate centroid
    let sum_x: usize = yellow_pixels.iter().map(|(x, _)| x).sum();
    let sum_y: usize = yellow_pixels.iter().map(|(_, y)| y).sum();
    let count = yellow_pixels.len();

    let center_x = (sum_x / count) as i32;
    let center_y = (sum_y / count) as i32;

    // Confidence based on pixel count (more pixels = more confident)
    let confidence = (count as f32 / 500.0).min(1.0);

    Some((center_x, center_y, confidence))
}

/// Find cyan Quest Helper highlight
/// Returns (x, y, confidence) if found
pub fn find_cyan_highlight(img_data: &[u8], width: u32, height: u32) -> Option<(i32, i32, f32)> {
    // Cyan highlight: R < 80, G > 180, B > 180

    let pixels_per_row = width as usize;
    let total_pixels = (width * height) as usize;

    if img_data.len() < total_pixels * 4 {
        return None;
    }

    let cyan_pixels: Vec<(usize, usize)> = (0..total_pixels)
        .into_par_iter()
        .filter_map(|i| {
            let offset = i * 4;
            let r = img_data[offset];
            let g = img_data[offset + 1];
            let b = img_data[offset + 2];

            // Cyan/turquoise detection
            if r < 80 && g > 180 && b > 180 {
                let x = i % pixels_per_row;
                let y = i / pixels_per_row;
                Some((x, y))
            } else {
                None
            }
        })
        .collect();

    if cyan_pixels.len() < 20 {
        return None;
    }

    let sum_x: usize = cyan_pixels.iter().map(|(x, _)| x).sum();
    let sum_y: usize = cyan_pixels.iter().map(|(_, y)| y).sum();
    let count = cyan_pixels.len();

    let center_x = (sum_x / count) as i32;
    let center_y = (sum_y / count) as i32;

    let confidence = (count as f32 / 1000.0).min(1.0);

    Some((center_x, center_y, confidence))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_yellow_detection() {
        // Create test image with yellow pixels
        let mut img = vec![0u8; 100 * 100 * 4];

        // Add yellow blob at (50, 50)
        for y in 45..55 {
            for x in 45..55 {
                let i = (y * 100 + x) * 4;
                img[i] = 255;     // R
                img[i + 1] = 255; // G
                img[i + 2] = 0;   // B
                img[i + 3] = 255; // A
            }
        }

        let result = find_yellow_arrow(&img, 100, 100);
        assert!(result.is_some());

        let (x, y, _) = result.unwrap();
        assert!((x - 50).abs() < 5);
        assert!((y - 50).abs() < 5);
    }
}
