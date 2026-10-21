// SPDX-License-Identifier: AGPL-3.0-or-later
// EditPop adaptation: exclusive import targets and confirmed disk writes.
package app.concat.editor;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

/** Copies one selected stream without overwriting an earlier import. */
public final class ImportFileTarget {
    private ImportFileTarget() {}

    /** Owns and closes source; returns only after copy, sync and close succeed. */
    public static File copy(InputStream source, File directory, String displayName) throws IOException {
        if (source == null) throw new IOException("the provider returned no input stream");
        File target = null;
        boolean complete = false;
        try {
            try (InputStream input = source) {
                if (!directory.isDirectory() && !directory.mkdirs() && !directory.isDirectory()) {
                    throw new IOException("the import folder is unavailable");
                }
                String name = displayName == null ? "import" : displayName.replace('/', '_').replace('\\', '_');
                if (name.isEmpty() || name.equals(".") || name.equals("..")) name = "import";
                int dot = name.lastIndexOf('.');
                String stem = dot > 0 ? name.substring(0, dot) : name;
                String ext = dot > 0 ? name.substring(dot) : "";
                for (int n = 1; n <= 10000; n++) {
                    File candidate = new File(directory, n == 1 ? name : stem + " (" + n + ")" + ext);
                    if (candidate.createNewFile()) { target = candidate; break; }
                }
                if (target == null) throw new IOException("too many files with the same name");
                try (FileOutputStream output = new FileOutputStream(target)) {
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (count == 0) {
                            int single = input.read();
                            if (single == -1) break;
                            output.write(single);
                        } else output.write(buffer, 0, count);
                    }
                    output.getFD().sync();
                }
            }
            complete = true;
            return target;
        } finally {
            if (!complete && target != null) target.delete();
        }
    }
}
