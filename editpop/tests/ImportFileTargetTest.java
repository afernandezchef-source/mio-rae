import app.concat.editor.ImportFileTarget;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public final class ImportFileTargetTest {
    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("editpop-import-test-");
        ExecutorService workers = Executors.newFixedThreadPool(4);
        try {
            Path original = root.resolve("video.mp4");
            Files.write(original, new byte[] {99});
            File copy = ImportFileTarget.copy(new ByteArrayInputStream(new byte[] {1,2,3}), root.toFile(), "video.mp4");
            check(!copy.toPath().equals(original), "existing import was reused");
            check(Arrays.equals(Files.readAllBytes(original), new byte[] {99}), "original changed");
            check(Arrays.equals(Files.readAllBytes(copy.toPath()), new byte[] {1,2,3}), "copy differs");
            List<Future<File>> results = new ArrayList<>();
            for (int i = 0; i < 12; i++) { final int n=i; results.add(workers.submit(() -> ImportFileTarget.copy(new ByteArrayInputStream(new byte[] {(byte)n}), root.toFile(), "same.wav"))); }
            Set<String> names = new HashSet<>();
            for (int i=0;i<results.size();i++) {File f=results.get(i).get();check(names.add(f.getName()), "concurrent imports collided");check(Files.readAllBytes(f.toPath())[0]==(byte)i, "concurrent import overwritten");}
            int before = root.toFile().list().length;
            InputStream broken = new InputStream() {int n; public int read() throws IOException {if(n>=5)throw new IOException("provider revoked"); n++; return 1;}};
            try {ImportFileTarget.copy(broken,root.toFile(),"failed.mp4");throw new AssertionError("read failure accepted");} catch(IOException expected){}
            check(root.toFile().list().length==before,"failed partial retained");
            InputStream closeFailure = new ByteArrayInputStream(new byte[] {7}) {public void close() throws IOException {throw new IOException("close failed");}};
            try {ImportFileTarget.copy(closeFailure,root.toFile(),"failed-close.mp4");throw new AssertionError("close failure accepted");} catch(IOException expected){}
            check(root.toFile().list().length==before,"close-failed partial retained");
            for(String name:new String[]{"../outside.mp4","..","/absolute.mp4"}) {
                File f=ImportFileTarget.copy(new ByteArrayInputStream(new byte[]{8}),root.toFile(),name);
                check(f.getCanonicalFile().getParentFile().equals(root.toFile().getCanonicalFile()),"escaped import folder");
            }
            AtomicBoolean closed = new AtomicBoolean();
            InputStream unavailable = new ByteArrayInputStream(new byte[] {4}) {public void close(){closed.set(true);}};
            try {ImportFileTarget.copy(unavailable,original.toFile(),"x");throw new AssertionError("invalid directory accepted");} catch(IOException expected){}
            check(closed.get(),"source leaked on directory failure");
            InputStream zeroRead = new ByteArrayInputStream(new byte[]{1,2,3}) {boolean first=true;public synchronized int read(byte[] b,int off,int len){if(first){first=false;return 0;}return super.read(b,off,len);}};
            File zero=ImportFileTarget.copy(zeroRead,root.toFile(),"zero-read.bin");
            check(Arrays.equals(Files.readAllBytes(zero.toPath()),new byte[]{1,2,3}),"zero read truncated stream");
            System.out.println("PASS: 7 scenarios (copy/collision, concurrent reservation, read failure, close failure, path containment, unavailable folder cleanup, zero-length read)");
        } finally {
            workers.shutdown(); workers.awaitTermination(10,TimeUnit.SECONDS);
            try(java.util.stream.Stream<Path> paths=Files.walk(root)){paths.sorted(Comparator.reverseOrder()).forEach(p->{try{Files.delete(p);}catch(IOException e){throw new UncheckedIOException(e);}});}
        }
    }
}
